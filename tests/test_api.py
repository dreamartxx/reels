import io
import wave
import pytest
from fastapi.testclient import TestClient
from backend import main


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DATA',tmp_path)
    return TestClient(main.app)


def wav():
    buf=io.BytesIO()
    with wave.open(buf,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*32000)
    return buf.getvalue()


def test_upload_manual_persistence_scene_and_bounds(client):
    r=client.post('/api/projects',files={'file':('ses.wav',wav(),'audio/wav')});assert r.status_code==200,r.text
    p=r.json();pid=p['id'];assert p['audio']['duration']==2
    r=client.post(f'/api/projects/{pid}/manual',json={'text':'[pause] İlk cümle. İkinci cümle.'});assert r.status_code==200,r.text
    p=r.json();assert len(p['sentences'])==2
    assert all(s['review'] for s in p['sentences'])
    assert p['alignment']['engine']=='manual'
    p['name']='Türkçe proje';assert client.put(f'/api/projects/{pid}',json=p).status_code==200
    assert client.get(f'/api/projects/{pid}').json()['name']=='Türkçe proje'
    r=client.post(f'/api/projects/{pid}/scene',json=p);assert r.status_code==200,r.text
    digest=r.json()['digest']
    assert client.get(f'/api/projects/{pid}/scenes/{digest}/0.png').headers['content-type']=='image/png'
    assert client.get(f'/api/projects/{pid}/audio',headers={'Range':'bytes=0-99'}).status_code==206
    p['sentences'][-1]['end']=3
    assert client.put(f'/api/projects/{pid}',json=p).status_code==422
    assert client.post(f'/api/projects/{pid}/export',json=p).status_code==422


def test_bad_upload_cleanup_and_path_rejection(client):
    assert client.post('/api/projects',files={'file':('fake.mp3',b'not an audio file','audio/mpeg')}).status_code==400
    assert client.get('/api/projects').json()==[]
    assert client.post('/api/projects',files={'file':('code.py',b'print(1)','text/plain')}).status_code==400
    assert client.get('/api/projects/not-a-uuid').status_code==404
