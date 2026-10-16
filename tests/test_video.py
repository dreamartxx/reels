import json
import subprocess
import time
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend import main, video
from backend.render import motion

ROOT = Path(__file__).resolve().parents[1]


def ffmpeg(*args):
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y',*map(str,args)],check=True,capture_output=True)


def test_portrait_background_lifecycle_and_uncut_export(tmp_path, monkeypatch):
    monkeypatch.setattr(main,'DATA',tmp_path/'projects');main.DATA.mkdir()
    wav=tmp_path/'voice.wav';clip=tmp_path/'nature.mp4';short=tmp_path/'short.mp4';landscape=tmp_path/'wide.mp4'
    ffmpeg('-f','lavfi','-i','sine=frequency=440:duration=1.2',wav)
    ffmpeg('-f','lavfi','-i','testsrc2=size=180x320:rate=30:duration=2.4','-c:v','libx264','-pix_fmt','yuv420p',clip)
    ffmpeg('-i',clip,'-t','0.5','-c','copy',short)
    ffmpeg('-f','lavfi','-i','color=size=320x180:duration=2','-c:v','libx264',landscape)
    with pytest.raises(ValueError,match='kısa'):video.probe(short,1.2)
    with pytest.raises(ValueError,match='9:16'):video.probe(landscape,1.2)
    def wait(client,job):
        for _ in range(300):
            r=client.get('/api/jobs/'+job['id']).json()
            if r['status'] in ('completed','failed','cancelled'):
                assert r['status']=='completed',r
                return r['result']
            time.sleep(.1)
        pytest.fail('Job did not complete')
    with TestClient(main.app) as client:
        with wav.open('rb') as f:p=client.post('/api/projects',files={'file':('voice.wav',f,'audio/wav')}).json()
        base='/api/projects/'+p['id']
        with short.open('rb') as f:assert client.post(base+'/background',files={'file':('short.mp4',f,'video/mp4')}).status_code==422
        with clip.open('rb') as f:r=client.post(base+'/background',files={'file':('nature.mp4',f,'video/mp4')})
        assert r.status_code==200,r.text
        p=wait(client,r.json());assert p['background']['duration']==pytest.approx(2.4,abs=.04)
        assert client.get(base+'/backgrounds/'+p['background']['id'],headers={'Range':'bytes=0-31'}).status_code==206
        p=client.post(base+'/manual',json={'text':'Doğa bize iyi gelir.'}).json()
        # Text autosave must preserve uploaded footage.
        edit={k:p[k] for k in ('name','text','style','sentences')}
        assert client.put(base,json=edit).json()['background']['id']==p['background']['id']
        result=wait(client,client.post(base+'/export',json={**edit,'quality':'preview'}).json())
        output=tmp_path/'result.mp4';output.write_bytes(client.get(result['files']['video.mp4']).content)
        assert video.probe(output)['duration']==pytest.approx(2.4,abs=.04)
        raw=subprocess.check_output(['ffmpeg','-v','error','-ss','1.6','-i',str(output),'-vn','-f','f32le','-ac','1','-'])
        assert np.max(np.abs(np.frombuffer(raw,dtype=np.float32)))<.001
        # Moving background remains after narration, with no text beyond audio end.
        def frame(path,t):
            return subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(path),'-frames:v','1','-vf','scale=90:160','-f','rawvideo','-pix_fmt','rgb24','-'])
        assert frame(output,1.7)!=frame(output,2.1)
        assert motion(edit['sentences'],1.7,.6,1.2,True)==[]
        normalized=main.DATA/p['id']/'backgrounds'/p['background']['id']/'video.mp4'
        expected=np.frombuffer(frame(normalized,1.7),dtype=np.uint8)*.65
        actual=np.frombuffer(frame(output,1.7),dtype=np.uint8).astype(float)
        assert np.mean(np.abs(actual-expected))<8
        assert client.delete(base+'/background').json()['background'] is None
        assert client.get(base).json()['audio']['duration']==pytest.approx(1.2)


def test_video_choreography_matches_canvas_and_stops_at_audio_end():
    s=[{'start':0},{'start':1.5},{'start':3.2}];times=[i/100 for i in range(600)]
    code='import {motion} from "./frontend/src/motion.ts";console.log(JSON.stringify('+json.dumps(times)+'.map(t=>motion('+json.dumps(s)+',t,.6,4.5,true))));'
    actual=json.loads(subprocess.check_output(['node','--experimental-strip-types','--input-type=module','-e',code],cwd=ROOT,text=True))
    for t,js in zip(times,actual):
        assert motion(s,t,.6,4.5,True)==js
        assert len(js)<=1
    assert motion(s,4.5,.6,4.5,True)==[]
