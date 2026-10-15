"""Verify final codecs, durations, full decode, black frames and audio time offset."""
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
video=Path(sys.argv[1])
source=ROOT/'examples/elevenlabs-kullanici.mp3'

def probe(path):
 return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
def samples(path):
 return np.frombuffer(subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(path),'-vn','-ac','1','-ar','8000','-f','f32le','-']),dtype=np.float32)
info=probe(video); original=probe(source)
v=next(s for s in info['streams'] if s['codec_type']=='video');a=next(s for s in info['streams'] if s['codec_type']=='audio')
assert (v['width'],v['height'],v['r_frame_rate'],v['codec_name'],v['pix_fmt'])==(1080,1920,'30/1','h264','yuv420p')
assert a['codec_name']=='aac'
assert abs(float(v['duration'])-float(original['format']['duration']))<1/30
assert abs(float(a['duration'])-float(original['format']['duration']))<.03
src,out=samples(source),samples(video)
checks=[]
for second in [2,45,90]:
 x=src[second*8000:(second+4)*8000];y=out[second*8000:(second+4)*8000]
 n=1<<(2*len(x)-1).bit_length();corr=np.fft.irfft(np.fft.rfft(y,n)*np.conj(np.fft.rfft(x,n)),n)
 lag=int(np.argmax(corr));lag=lag-n if lag>n//2 else lag
 similarity=float(np.corrcoef(x,y)[0,1]);assert abs(lag)<=8;assert similarity>.98
 checks.append({'at_seconds':second,'lag_ms':lag/8,'correlation':similarity})
r=subprocess.run(['ffmpeg','-nostdin','-v','info','-i',str(video),'-vf','blackdetect=d=0.02:pix_th=0.005:pic_th=0.999','-an','-f','null','-'],capture_output=True,text=True)
assert r.returncode==0,r.stderr[-1000:]
assert 'black_start:' not in r.stderr
report={'video':str(video),'resolution':[v['width'],v['height']],'fps':v['r_frame_rate'],'video_codec':v['codec_name'],'audio_codec':a['codec_name'],'source_duration':float(original['format']['duration']),'video_duration':float(v['duration']),'audio_duration':float(a['duration']),'full_decode':'passed','black_frames':'none detected','audio_checks':checks}
(ROOT/'examples/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
