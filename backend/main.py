import importlib.util
import json
import os
import re
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from . import audio, alignment, render
from .downloads import download_name
from .models import AlignmentRequest, Edit, ExportRequest, Style
from .text import clean_text, split_poem, srt

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv('REELS_DATA_DIR', str(ROOT/'data')))
DATA.mkdir(parents=True, exist_ok=True)
app = FastAPI(title='Reels Typography Studio')
POOL = ThreadPoolExecutor(max_workers=1)
JOBS = {}
LOCK = threading.RLock()


def folder(pid):
    if not re.fullmatch(r'[a-f0-9]{32}', pid):
        raise HTTPException(404, 'Proje bulunamadı.')
    target = DATA/pid
    if not (target/'project.json').exists():
        raise HTTPException(404, 'Proje bulunamadı.')
    return target


def read_project(pid):
    with LOCK:
        return json.loads((folder(pid)/'project.json').read_text(encoding='utf-8'))


def write_project(target, p):
    p['updated_at'] = time.time()
    with LOCK:
        temp = target/'project.tmp'
        temp.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(target/'project.json')


def validate_edit(p, edit):
    if edit.sentences and edit.sentences[-1].end > p['audio']['duration']+.001:
        raise HTTPException(422, 'Cümle bitişi ses süresini aşamaz.')


def job(pid, kind, task):
    with LOCK:
        active = [j for j in JOBS.values() if j['status'] in ('queued','running')]
        if any(j['project_id'] == pid for j in active):
            raise HTTPException(409, 'Bu projede devam eden işlem var.')
        if len(active) >= 3:
            raise HTTPException(429, 'İşlem sırası dolu. Devam eden işlemin bitmesini bekleyin.')
        jid = uuid.uuid4().hex
        record = {'id': jid, 'project_id': pid, 'kind': kind, 'status': 'queued', 'progress': 0, 'message': 'Sırada…', 'cancel': False}
        JOBS[jid] = record
    def progress(value, message):
        if record['cancel']:
            raise RuntimeError('İşlem iptal edildi.')
        record.update(progress=value, message=message)
    def run():
        record['status'] = 'running'
        try:
            progress(0, 'Başlatılıyor…')
            result = task(jid, progress, lambda: record['cancel'])
            record.update(status='completed', result=result, progress=1)
        except Exception as e:
            record.update(status='cancelled' if record['cancel'] else 'failed', message=str(e))
    POOL.submit(run)
    return record


@app.get('/api/health')
def health():
    return {'ffmpeg': bool(shutil.which('ffmpeg')), 'ffprobe': bool(shutil.which('ffprobe')), 'alignment': importlib.util.find_spec('stable_whisper') is not None, 'models': [p.stem for p in (DATA/'models').glob('*.pt')], 'version': '1.0.0'}


@app.get('/api/fonts/{font}')
def font_file(font: str):
    if font not in ('serif','sans','mono'):
        raise HTTPException(404)
    return FileResponse(ROOT/'assets'/'fonts'/f'{font}.ttf')


@app.get('/api/projects')
def projects():
    with LOCK:
        items = [json.loads(p.read_text(encoding='utf-8')) for p in DATA.glob('*/project.json')]
    return sorted([{'id': p['id'], 'name': p['name'], 'duration': p['audio']['duration'], 'updated_at': p['updated_at']} for p in items], key=lambda p: p['updated_at'], reverse=True)


@app.post('/api/projects')
def create(file: UploadFile = File(...)):
    extension = Path(file.filename or '').suffix.lower()
    if extension not in ('.mp3','.wav'):
        raise HTTPException(400, 'MP3 veya WAV dosyası yükleyin.')
    pid = uuid.uuid4().hex
    target = DATA/pid
    target.mkdir()
    path = target/f'audio{extension}'
    try:
        size = 0
        with path.open('wb') as out:
            while chunk := file.file.read(1024*1024):
                size += len(chunk)
                if size > 100*1024*1024:
                    raise ValueError('Dosya en fazla 100 MB olabilir.')
                out.write(chunk)
        meta = audio.probe(path)
        waveform = audio.prepare(path, target/'alignment.wav')
        p = {'id': pid, 'name': Path(file.filename).stem[:120] or 'İsimsiz şiir', 'text': '', 'style': Style().model_dump(), 'sentences': [], 'audio': {**meta, 'filename': file.filename, 'file': path.name, 'waveform': waveform}, 'alignment': None}
        write_project(target, p)
        return p
    except Exception as e:
        shutil.rmtree(target, ignore_errors=True)
        raise HTTPException(400, str(e)) from e
    finally:
        file.file.close()


@app.get('/api/projects/{pid}')
def get_project(pid: str):
    return read_project(pid)


@app.put('/api/projects/{pid}')
def save(pid: str, edit: Edit):
    p = read_project(pid)
    validate_edit(p, edit)
    p.update(edit.model_dump())
    write_project(folder(pid), p)
    return p


@app.get('/api/projects/{pid}/audio')
def get_audio(pid: str):
    p = read_project(pid)
    return FileResponse(folder(pid)/p['audio']['file'])


@app.post('/api/projects/{pid}/align')
def start_alignment(pid: str, req: AlignmentRequest):
    p = read_project(pid)
    try:
        split_poem(req.text, req.mode)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    def task(jid, progress, cancelled):
        sentences = alignment.align(folder(pid)/'alignment.wav', req.text, req.mode, req.model, req.device, DATA/'models', progress)
        duration = p['audio']['duration']
        for s in sentences:
            if s['start'] >= duration-.03:
                raise ValueError('Metnin sonu ses dosyasına sığmadı. Şiiri ve ses dosyasını kontrol edin.')
            if s['end'] > duration:
                s.update(end=duration, review=True, reason='Son kelime ses sınırında; kontrol edin.')
        if cancelled():
            raise RuntimeError('İşlem iptal edildi.')
        current = read_project(pid)
        current.update(text=clean_text(req.text), sentences=sentences, alignment={'engine':'stable-ts', 'model':req.model, 'language':'tr', 'mode':req.mode})
        write_project(folder(pid), current)
        return current
    return job(pid, 'align', task)


@app.post('/api/projects/{pid}/manual')
def manual(pid: str, req: AlignmentRequest):
    p = read_project(pid)
    try:
        parts = split_poem(req.text, req.mode)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    duration = p['audio']['duration']
    if duration/len(parts) < .04:
        raise HTTPException(422, 'Bu ses süresi için çok fazla cümle var.')
    weights = [len(x.split()) for x in parts]
    cursor, sentences = 0., []
    for i, (part, weight) in enumerate(zip(parts, weights)):
        end = cursor + duration*weight/sum(weights)
        sentences.append({'id':f's{i+1}', 'text':part, 'start':cursor, 'end':min(end,duration), 'review':True, 'reason':'Elle zamanlama taslağı; sesle hizalanmadı.', 'accent':False, 'words':[]})
        cursor = end
    p.update(text=clean_text(req.text), sentences=sentences, alignment={'engine':'manual'})
    write_project(folder(pid), p)
    return p


@app.post('/api/projects/{pid}/scene')
def scene(pid: str, edit: Edit):
    p = read_project(pid)
    validate_edit(p, edit)
    try:
        return render.build_scene(folder(pid), [s.model_dump() for s in edit.sentences], edit.style.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@app.get('/api/projects/{pid}/scenes/{digest}/{filename}')
def asset(pid: str, digest: str, filename: str):
    if not re.fullmatch(r'[a-f0-9]{20}', digest) or not re.fullmatch(r'(background\.jpg|\d+\.png)', filename):
        raise HTTPException(404)
    path = folder(pid)/'scenes'/digest/filename
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, headers={'Cache-Control': 'public, max-age=31536000, immutable'})


@app.post('/api/projects/{pid}/export')
def export(pid: str, req: ExportRequest):
    p = read_project(pid)
    validate_edit(p, req)
    if not req.sentences:
        raise HTTPException(422, 'Önce metni hizalayın veya elle zamanlayın.')
    snapshot = req.model_dump(exclude={'quality'})
    def task(jid, progress, cancelled):
        out = folder(pid)/'exports'/jid
        out.mkdir(parents=True)
        render.render_video(folder(pid), folder(pid)/p['audio']['file'], snapshot['sentences'], snapshot['style'], p['audio']['duration'], out/'video.mp4', req.quality=='preview', progress, cancelled)
        timing = {**snapshot, 'duration':p['audio']['duration'], 'alignment':p.get('alignment'), 'sentences':[]}
        for i, s in enumerate(snapshot['sentences']):
            next_start = snapshot['sentences'][i+1]['start'] if i+1 < len(snapshot['sentences']) else p['audio']['duration']
            timing['sentences'].append({**s, 'pause_after':max(0,next_start-s['end']), 'display_start':0 if i==0 else s['start'], 'display_end':next_start})
        (out/'timing.json').write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding='utf-8')
        (out/'subtitles.srt').write_text(srt(snapshot['sentences']), encoding='utf-8')
        return {'files':{name:f'/api/projects/{pid}/exports/{jid}/{name}' for name in ('video.mp4','timing.json','subtitles.srt')}}
    return job(pid, 'export', task)


@app.get('/api/projects/{pid}/exports')
def exports(pid: str):
    return [{'id':d.name, 'files':{name:f'/api/projects/{pid}/exports/{d.name}/{name}' for name in ('video.mp4','timing.json','subtitles.srt')}} for d in sorted((folder(pid)/'exports').glob('*'), key=lambda d:d.stat().st_mtime, reverse=True) if (d/'timing.json').exists()]


@app.get('/api/projects/{pid}/exports/{jid}/{filename}')
def download(pid: str, jid: str, filename: str):
    if not re.fullmatch(r'[a-f0-9]{32}', jid) or filename not in ('video.mp4','timing.json','subtitles.srt'):
        raise HTTPException(404)
    path = folder(pid)/'exports'/jid/filename
    if not path.exists():
        raise HTTPException(404)
    snapshot = json.loads((path.parent/'timing.json').read_text())
    name = download_name(snapshot.get('name', 'reels'), (path.parent/'video.mp4').stat().st_mtime, jid, filename)
    return FileResponse(path, filename=name)


@app.get('/api/projects/{pid}/jobs')
def project_jobs(pid: str):
    folder(pid)
    return [j for j in JOBS.values() if j['project_id'] == pid and j['status'] in ('queued', 'running')]


@app.get('/api/jobs/{jid}')
def get_job(jid: str):
    if jid not in JOBS:
        raise HTTPException(404, 'İşlem bulunamadı; sunucu yeniden başlatılmış olabilir.')
    return JOBS[jid]


@app.post('/api/jobs/{jid}/cancel')
def cancel_job(jid: str):
    record = get_job(jid)
    record['cancel'] = True
    return {'message':'İptal isteniyor; model işlemi güvenli noktada duracak.'}


@app.get('/api/example/audio')
def example_audio():
    path = ROOT/'examples'/'turkce-ornek.mp3'
    if not path.exists():
        raise HTTPException(404, 'Örnek ses bulunamadı.')
    return FileResponse(path)


FRONTEND = ROOT/'frontend'/'dist'
if FRONTEND.exists():
    app.mount('/', StaticFiles(directory=FRONTEND, html=True), name='frontend')
