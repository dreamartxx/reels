"""Exercise the PHP queue, worker and protected background media on local test hosting."""
import json,subprocess,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
cache=ROOT/'.private/test-cloud';c=httpx.Client(base_url='http://127.0.0.1:8766',timeout=120)
def check(r):r.raise_for_status();return r.json()
check(c.post('/api/auth/login',json={'password':'test-password-only'}))
for name,src in [('background-test.wav','sine=frequency=440:duration=2'),('background-test.mp4','testsrc2=size=180x320:rate=30:duration=4')]:
 subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-f','lavfi','-i',src,str(cache/name)],check=True)
worker=subprocess.Popen([str(ROOT/'.venv/bin/python'),'cloud/worker.py','--config',str(cache/'worker.json')],cwd=ROOT,stdout=(cache/'video-worker.log').open('w'),stderr=subprocess.STDOUT)
def wait(jid,fail=False):
 for _ in range(200):
  j=check(c.get('/api/jobs/'+jid))
  if j['status'] in ('completed','failed','cancelled'):
   assert j['status']==('failed' if fail else 'completed'),j
   return j.get('result') if not fail else j
  time.sleep(.2)
 raise TimeoutError(jid)
try:
 with (cache/'background-test.wav').open('rb') as f:p=check(c.post('/api/projects',files={'file':('test.wav',f,'audio/wav')}))
 base='/api/projects/'+p['id'];wait(check(c.get(base+'/jobs'))[0]['id'])
 p=check(c.post(base+'/manual',json={'text':'Video devam ediyor.','mode':'sentences'}))
 with (cache/'background-test.mp4').open('rb') as f:j=check(c.post(base+'/background',files={'file':('test.mp4',f,'video/mp4')}))
 p=wait(j['id']);assert p['background']['duration']==4
 url=base+'/backgrounds/'+p['background']['id']
 assert c.get(url,headers={'Range':'bytes=0-31'}).status_code==206
 assert httpx.get(str(c.base_url).rstrip('/')+url).status_code==401
 assert c.get('/api/worker/jobs/'+j['id']+'/source').status_code==403
 result=wait(check(c.post(base+'/export',json={**p,'quality':'preview'}))['id'])
 output=cache/'background-result.mp4';output.write_bytes(c.get(result['files']['video.mp4']).content)
 from backend.video import probe
 assert probe(output)['duration']==4
 assert check(c.delete(base+'/background'))['background'] is None
 print('PASS: PHP upload, background job, worker normalization, private/ranged video, uncut 4-second export from 2-second voice, removal')
finally:worker.terminate();worker.wait(timeout=10)
