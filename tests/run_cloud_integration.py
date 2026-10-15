"""Local PHP protocol integration. Requires the test PHP server on port 8766."""
import json,subprocess,sys,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
c=httpx.Client(base_url='http://127.0.0.1:8766',timeout=120)
def check(r):
 r.raise_for_status();return r.json()
assert c.get('/api/projects').status_code==401
assert c.post('/api/auth/login',json={'password':'wrong'}).status_code==401
check(c.post('/api/auth/login',json={'password':'test-password-only'}))
assert c.get('/api/health').json()['authenticated']
assert c.post('/api/projects',headers={'Origin':'https://attacker.invalid'},json={}).status_code==403
with (ROOT/'examples/turkce-ornek.mp3').open('rb') as f:p=check(c.post('/api/projects',files={'file':('test.mp3',f,'audio/mpeg')}))
pid=p['id'];assert p['audio']['duration']==0
worker=subprocess.Popen([str(ROOT/'.venv/bin/python'),'cloud/worker.py','--config',str(ROOT/'.private/test-cloud/worker.json')],cwd=ROOT,stdout=(ROOT/'.private/test-cloud/worker.log').open('w'),stderr=subprocess.STDOUT)
def wait(jid):
 for _ in range(180):
  j=check(c.get('/api/jobs/'+jid))
  if j['status']=='completed':return j['result']
  if j['status'] in ('failed','cancelled'):raise AssertionError(j)
  time.sleep(.5)
 raise TimeoutError(jid)
try:
 jobs=check(c.get(f'/api/projects/{pid}/jobs'));p=wait(jobs[0]['id']);assert p['audio']['duration']>10
 assert c.get(f'/api/projects/{pid}/audio',headers={'Range':'bytes=0-99'}).status_code==206
 p.update(name='Bulut entegrasyon testi',text=(ROOT/'examples/siir.txt').read_text());p=check(c.put(f'/api/projects/{pid}',json=p))
 j=check(c.post(f'/api/projects/{pid}/align',json={'text':p['text'],'model':'base'}));p=wait(j['id']);assert len(p['sentences'])==4
 scene=check(c.post(f'/api/projects/{pid}/scene',json=p));assert scene['pending'];scene=wait(scene['job']);assert len(scene['sprites'])==4
 assert check(c.post(f'/api/projects/{pid}/scene',json=p))['digest']==scene['digest']
 assert c.get(f'/api/projects/{pid}/scenes/{scene["digest"]}/0.png').status_code==200
 j=check(c.post(f'/api/projects/{pid}/export',json={**p,'quality':'preview'}));result=wait(j['id']);assert len(result['files'])==3
 for name,url in result['files'].items():
  r=c.get(url);r.raise_for_status();assert len(r.content)>10
  if name=='video.mp4':(ROOT/'.private/test-cloud/video.mp4').write_bytes(r.content)
 unauth=httpx.Client(base_url=c.base_url)
 assert unauth.get(result['files']['video.mp4']).status_code==401
 assert unauth.get(f'/api/projects/{pid}/audio').status_code==401
 print('PASS: auth, CSRF, upload, ingest, original-text alignment, scene cache, render, audio range, protected downloads')
finally:
 worker.terminate();worker.wait(timeout=10)
