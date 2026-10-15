"""Outbound-only worker for the Hostinger/MySQL queue. No inbound port or tunnel."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
import zipfile
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend import audio, alignment, render
from backend.models import Edit, AlignmentRequest
from backend.text import clean_text,srt

class Worker:
    def __init__(self, config):
        self.url=config['url'].rstrip('/')
        if not self.url.startswith('https://') and not self.url.startswith('http://127.0.0.1:'):
            raise ValueError('Motor yalnızca HTTPS veya yerel test sunucusuna bağlanır.')
        self.client=httpx.Client(base_url=self.url,headers={'Authorization':'Bearer '+config['worker_token']},timeout=120,follow_redirects=False)
        self.cache=ROOT/'data'/'cloud-cache'
        self.cache.mkdir(parents=True,exist_ok=True)
        self.once=False
    def post(self,path,data):
        r=self.client.post('/api'+path,json=data);r.raise_for_status();return r.json()
    def source(self,p):
        folder=self.cache/p['id'];folder.mkdir(exist_ok=True)
        path=folder/p['audio']['file']
        if not path.exists():
            with self.client.stream('GET','/api/projects/'+p['id']+'/audio') as response:
                response.raise_for_status()
                with path.with_suffix('.tmp').open('wb') as out:
                    size=0
                    for chunk in response.iter_bytes():
                        size+=len(chunk)
                        if size>100*1024*1024:raise ValueError('Ses dosyası boyut sınırını aşıyor.')
                        out.write(chunk)
            path.with_suffix('.tmp').replace(path)
        return folder,path
    def execute(self,j):
        jid,lease,p,payload=j['id'],j['lease'],j['project'],j['payload']
        endpoint='/worker/jobs/'+jid
        state={'progress':0.,'message':'Başlatılıyor…'}
        done,cancelled=threading.Event(),threading.Event()
        def heartbeat():
            while not done.wait(8):
                try:
                    result=self.post(endpoint+'/progress',{'lease':lease,**state})
                    if result.get('cancel'):cancelled.set()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (401,403,409):cancelled.set()
                except httpx.HTTPError:
                    pass
        def progress(value,message):
            if cancelled.is_set():raise RuntimeError('İşlem iptal edildi veya başka bir motora geçti.')
            state.update(progress=value,message=message)
        thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
        archive=None
        try:
            if j['kind']=='ingest':
                folder,path=self.source(p);meta=audio.probe(path)
                progress(.2,'Ses dosyası analiz ediliyor…')
                peaks=audio.prepare(path,folder/'alignment.wav')
                result={'audio':{**meta,'waveform':peaks}}
            elif j['kind']=='align':
                req=AlignmentRequest.model_validate(payload);folder,path=self.source(p)
                if not (folder/'alignment.wav').exists():audio.prepare(path,folder/'alignment.wav')
                sentences=alignment.align(folder/'alignment.wav',req.text,req.mode,req.model,req.device,ROOT/'data'/'models',progress)
                for s in sentences:
                    if s['start']>=p['audio']['duration']-.03:raise ValueError('Metnin sonu ses dosyasına sığmadı.')
                    if s['end']>p['audio']['duration']:s.update(end=p['audio']['duration'],review=True,reason='Son kelime ses sınırında.')
                result={'text':clean_text(req.text),'sentences':sentences,'alignment':{'engine':'stable-ts','model':req.model,'mode':req.mode,'language':'tr'}}
            elif j['kind']=='scene':
                edit=Edit.model_validate(payload);folder=self.cache/p['id'];folder.mkdir(exist_ok=True)
                result=render.build_scene(folder,[s.model_dump() for s in edit.sentences],edit.style.model_dump())
                archive=folder/(jid+'.zip')
                with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
                    for name in ['background.jpg']+[s['file'] for s in result['sprites']]:z.write(folder/'scenes'/result['digest']/name,name)
            elif j['kind']=='export':
                edit=Edit.model_validate(payload);folder,path=self.source(p);out=folder/'exports'/jid;out.mkdir(parents=True,exist_ok=True)
                sentences=[s.model_dump() for s in edit.sentences]
                if not sentences or sentences[-1]['end']>p['audio']['duration']+.001:raise ValueError('Geçersiz cümle zamanları.')
                render.render_video(folder,path,sentences,edit.style.model_dump(),p['audio']['duration'],out/'video.mp4',payload.get('quality')=='preview',progress,cancelled.is_set)
                timing=edit.model_dump();timing.update(duration=p['audio']['duration'],alignment=p.get('alignment'))
                for i,s in enumerate(timing['sentences']):
                    next_start=sentences[i+1]['start'] if i+1<len(sentences) else p['audio']['duration']
                    s.update(pause_after=max(0,next_start-s['end']),display_start=0 if i==0 else s['start'],display_end=next_start)
                (out/'timing.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2),encoding='utf-8')
                (out/'subtitles.srt').write_text(srt(sentences),encoding='utf-8')
                archive=folder/(jid+'.zip')
                with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
                    for name in ['video.mp4','subtitles.srt','timing.json']:z.write(out/name,name)
                result={}
            else:raise ValueError('Bilinmeyen iş türü.')
            progress(.99,'Sonuç Hostinger’a kaydediliyor…')
            data={'lease':lease,'data':result}
            if archive:
                with archive.open('rb') as f:
                    response=self.client.post('/api'+endpoint+'/complete',data={'result':json.dumps(data,ensure_ascii=False)},files={'archive':('result.zip',f,'application/zip')})
                response.raise_for_status()
            else:self.post(endpoint+'/complete',data)
            print(j['kind'],jid,'tamamlandı',flush=True)
        except Exception as e:
            message=str(e)
            # HTTP error URLs never include tokens. Keep private response data out of logs.
            print(j['kind'],jid,'başarısız:',message,flush=True)
            try:self.post(endpoint+'/fail',{'lease':lease,'message':message[:900]})
            except httpx.HTTPError:pass
        finally:
            done.set();thread.join(timeout=2)
            if archive:archive.unlink(missing_ok=True)
    def run(self,once=False):
        print('Reels motoru bağlandı:',self.url,flush=True)
        while True:
            try:
                result=self.post('/worker/claim',{})
                if result['job']:self.execute(result['job'])
                elif once:return
                else:time.sleep(2)
            except KeyboardInterrupt:return
            except httpx.HTTPError as e:
                print('Bağlantı bekleniyor:',type(e).__name__,flush=True)
                if once:raise
                time.sleep(10)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',default=str(ROOT/'.private'/'worker.json'));parser.add_argument('--once',action='store_true');args=parser.parse_args()
    path=Path(args.config)
    if not path.exists():raise SystemExit('Motor bağlantısı kurulmamış. hostinger/README.md dosyasına bakın.')
    Worker(json.loads(path.read_text())).run(args.once)
