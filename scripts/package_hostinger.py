"""Build deployable public_html plus non-secret private schema/template."""
import json
from pathlib import Path
import shutil
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.models import Style
out=ROOT/'build'/'hostinger';public=out/'public_html';public.mkdir(parents=True,exist_ok=True)
shutil.copytree(ROOT/'frontend/dist',public,dirs_exist_ok=True)
shutil.copytree(ROOT/'hostinger/public',public,dirs_exist_ok=True)
shutil.copytree(ROOT/'assets/fonts',public/'fonts',dirs_exist_ok=True)
(public/'fonts'/'serif').unlink(missing_ok=True)
(public/'default-style.json').write_text(json.dumps(Style().model_dump()))
shutil.copyfile(ROOT/'examples/turkce-ornek.mp3',public/'example.mp3')
private=out/'reels-private';private.mkdir(exist_ok=True)
shutil.copyfile(ROOT/'hostinger/private/schema.sql',private/'schema.sql')
shutil.copyfile(ROOT/'hostinger/private/config.example.php',private/'config.example.php')
with zipfile.ZipFile(ROOT/'build'/'reels-hostinger.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in out.rglob('*'):
  if p.is_file() and p.name!='config.php' and 'storage' not in p.parts:z.write(p,p.relative_to(out))
print(ROOT/'build/reels-hostinger.zip')
