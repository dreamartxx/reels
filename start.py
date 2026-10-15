"""Cross-platform entry point. Run after the README installation steps."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import threading
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
venv_python=ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if sys.prefix==sys.base_prefix and venv_python.exists():
    os.execv(str(venv_python),[str(venv_python),str(__file__),*sys.argv[1:]])
if sys.version_info<(3,11):
    raise SystemExit('Python 3.11 veya üstü gerekli. README dosyasına bakın.')
missing=[p for p in ('fastapi','uvicorn','PIL','stable_whisper','multipart') if importlib.util.find_spec(p) is None]
if missing:
    raise SystemExit('Eksik bağımlılıklar: '+', '.join(missing)+'\nÖnce: python -m pip install -r requirements.txt')
if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
    raise SystemExit('FFmpeg/ffprobe bulunamadı. README içindeki FFmpeg kurulumunu tamamlayın.')
if not (ROOT/'frontend'/'dist'/'index.html').exists():
    raise SystemExit('Arayüz derlenmedi. Önce: cd frontend && npm install && npm run build')
parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,default=8765)
parser.add_argument('--no-browser',action='store_true')
args=parser.parse_args()
url=f'http://127.0.0.1:{args.port}'
if not args.no_browser:
    def open_when_ready():
        import time
        for _ in range(30):
            try:
                with urllib.request.urlopen(url+'/api/health',timeout=1) as r:
                    if r.status==200:
                        webbrowser.open(url)
                        return
            except OSError:
                time.sleep(.5)
    threading.Thread(target=open_when_ready,daemon=True).start()
print(f'\nReels Typography Studio → {url}\nDurdurmak için Ctrl+C\n')
import uvicorn
uvicorn.run('backend.main:app',host='127.0.0.1',port=args.port)
