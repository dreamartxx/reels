"""Exercise the live HTTP API with the supplied real ElevenLabs recording."""
import json
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
client = httpx.Client(base_url='http://127.0.0.1:8765', timeout=120)
with (ROOT/'examples'/'elevenlabs-kullanici.mp3').open('rb') as f:
    response = client.post('/api/projects', files={'file':('ElevenLabs — İnsan bir gün susuyor.mp3', f, 'audio/mpeg')})
response.raise_for_status()
p = response.json()
text = (ROOT/'examples'/'insan-bir-gun-susuyor.txt').read_text()
p.update(name='İnsan bir gün susuyor', text=text)
response = client.put('/api/projects/'+p['id'], json=p)
response.raise_for_status()
(ROOT/'examples'/'project-id.txt').write_text(p['id'])
print('PROJECT',p['id'],p['audio']['duration'],flush=True)
response = client.post('/api/projects/'+p['id']+'/align', json={'text':text,'model':'base','mode':'sentences','device':'cpu'})
response.raise_for_status()
job = response.json()
print('JOB',job['id'],flush=True)
last=''
while job['status'] in ('running','queued'):
    time.sleep(2)
    response=client.get('/api/jobs/'+job['id']);response.raise_for_status();job=response.json()
    state=f'{job["status"]} {job["progress"]:.2f} {job["message"]}'
    if state!=last:print(state,flush=True);last=state
if job['status']!='completed':raise RuntimeError(job)
p=job['result']
(ROOT/'examples'/'alignment-result.json').write_text(json.dumps(p,ensure_ascii=False,indent=2))
print('SENTENCES',len(p['sentences']),'REVIEW',sum(s['review'] for s in p['sentences']),flush=True)
for s in p['sentences']:print(round(s['start'],2),round(s['end'],2),s['review'],s['text'],flush=True)
