"""Manage the current user's Reels worker with macOS launchd."""
import argparse
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'com.reels.typography.worker'
DOMAIN = f'gui/{os.getuid()}'
PLIST = Path.home()/'Library/LaunchAgents'/f'{LABEL}.plist'


def running():
    return subprocess.run(['launchctl','print',f'{DOMAIN}/{LABEL}'],capture_output=True,text=True)


def install():
    if not (ROOT/'.private/worker.json').is_file():
        raise SystemExit('Motor bağlantısı bulunamadı: .private/worker.json')
    logs = ROOT/'.private/logs'
    logs.mkdir(parents=True,exist_ok=True)
    bins = [str(ROOT/'.venv/bin')]
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg: bins.append(str(Path(ffmpeg).parent))
    bins.extend(['/opt/homebrew/bin','/usr/local/bin','/usr/bin','/bin','/usr/sbin','/sbin'])
    config = {
        'Label':LABEL,
        'ProgramArguments':[str(ROOT/'.venv/bin/python'),'-u',str(ROOT/'cloud/worker.py')],
        'WorkingDirectory':str(ROOT),
        'EnvironmentVariables':{'PATH':':'.join(dict.fromkeys(bins)),'PYTHONUNBUFFERED':'1'},
        'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':30,
        'ProcessType':'Background',
        'StandardOutPath':str(logs/'worker.log'),
        'StandardErrorPath':str(logs/'worker-error.log'),
    }
    encoded = plistlib.dumps(config)
    status = running()
    if status.returncode == 0:
        if not PLIST.is_file() or PLIST.read_bytes() != encoded:
            raise SystemExit('Motor servisi zaten yüklü; devam eden işi kesmemek için değiştirilmedi.')
        print('Otomatik video motoru zaten açık.')
        return
    PLIST.parent.mkdir(parents=True,exist_ok=True)
    PLIST.write_bytes(encoded)
    PLIST.chmod(0o600)
    result = subprocess.run(['launchctl','bootstrap',DOMAIN,str(PLIST)],capture_output=True,text=True)
    if result.returncode:
        raise SystemExit('Motor servisi başlatılamadı: '+result.stderr.strip())
    print('Video motoru arka planda başlatıldı. Mac oturumunuz açıldığında otomatik çalışır.')


def main():
    if sys.platform != 'darwin': raise SystemExit('Bu yardımcı macOS içindir.')
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['install','status','uninstall']);args=parser.parse_args()
    if args.action=='install':install()
    elif args.action=='status':
        r=running();print(r.stdout if r.returncode==0 else 'Otomatik motor servisi kapalı.')
    else:
        if running().returncode==0:
            subprocess.run(['launchctl','bootout',f'{DOMAIN}/{LABEL}'],check=True)
        PLIST.unlink(missing_ok=True)
        print('Otomatik başlatma kapatıldı. Projeleriniz ve çıktılarınız korunuyor.')

if __name__=='__main__':main()
