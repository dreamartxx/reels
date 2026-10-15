"""Generate private runtime configuration; never prints passwords or keys."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--url',required=True);parser.add_argument('--database',required=True);parser.add_argument('--user',required=True);parser.add_argument('--host',default='localhost');parser.add_argument('--credentials-file');args=parser.parse_args()
private=ROOT/'.private';private.mkdir(exist_ok=True,mode=0o700)
if args.credentials_file:
 inputs=json.loads(Path(args.credentials_file).read_text());db_password=inputs['db_password'];password=inputs.get('studio_password') or secrets.token_urlsafe(18);token=inputs.get('worker_token') or secrets.token_urlsafe(32)
else:db_password=getpass.getpass('Hostinger MySQL parolası: ');password=secrets.token_urlsafe(18);token=secrets.token_urlsafe(32)
hashed=subprocess.check_output(['php','-r','$p=stream_get_contents(STDIN);echo password_hash($p,PASSWORD_DEFAULT);'],input=password.encode()).decode()
settings={'dsn':f'mysql:host={args.host};dbname={args.database};charset=utf8mb4','db_user':args.user,'db_password':db_password,'origin':args.url.rstrip('/'),'password_hash':hashed,'worker_hash':hashlib.sha256(token.encode()).hexdigest()}
# JSON embedded as base64 is not encryption; the config MUST live outside the web root.
import base64
encoded=base64.b64encode(json.dumps(settings).encode()).decode()
config="<?php\n$c=json_decode(base64_decode('"+encoded+"'),true);\n$c['storage']=__DIR__.'/storage';\nreturn $c;\n"
(private/'config.php').write_text(config);(private/'worker.json').write_text(json.dumps({'url':args.url,'worker_token':token},indent=2))
(private/'studio-access.txt').write_text(f'Site: {args.url}\nStüdyo parolası: {password}\n')
for path in private.iterdir():
 if path.is_file():path.chmod(0o600)
print('Özel yapılandırma .private/ klasörüne yazıldı. Bu dosyaları GitHub’a eklemeyin.')
