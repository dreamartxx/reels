import json,time
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[1]
pid=(root/'examples/project-id.txt').read_text().strip()
c=httpx.Client(base_url='http://127.0.0.1:8765',timeout=120)
r=c.post(f'/api/projects/{pid}/align',json={'text':(root/'examples/insan-bir-gun-susuyor.txt').read_text(),'model':'small','mode':'sentences','device':'cpu'});r.raise_for_status();j=r.json()
print('JOB',j['id'],flush=True)
last=''
while j['status'] in ('running','queued'):
 time.sleep(2);r=c.get('/api/jobs/'+j['id']);r.raise_for_status();j=r.json()
 state=f'{j["status"]} {j["progress"]:.2f} {j["message"]}'
 if state!=last:print(state,flush=True);last=state
if j['status']!='completed':raise RuntimeError(j)
p=j['result'];(root/'examples/alignment-small.json').write_text(json.dumps(p,ensure_ascii=False,indent=2))
print('SENTENCES',len(p['sentences']),'REVIEW',sum(s['review'] for s in p['sentences']),flush=True)
