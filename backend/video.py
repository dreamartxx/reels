"""Validate and prepare user-owned portrait footage for playback and export."""
import json
import math
import subprocess
import time
from pathlib import Path
from .audio import binary

MAX_BYTES = 100*1024*1024


def probe(path: Path, audio_duration=0):
    r = subprocess.run([binary('ffprobe'), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, timeout=30)
    if r.returncode:
        raise ValueError('Video okunamadı. Geçerli MP4 veya MOV yükleyin.')
    info = json.loads(r.stdout)
    stream = next((s for s in info.get('streams', []) if s.get('codec_type') == 'video' and not s.get('disposition', {}).get('attached_pic')), None)
    if not stream:
        raise ValueError('Dosyada video görüntüsü bulunamadı.')
    width, height = int(stream['width']), int(stream['height'])
    rotation = next((float(s['rotation']) for s in stream.get('side_data_list', []) if 'rotation' in s), float(stream.get('tags', {}).get('rotate', 0)))
    if round(rotation) % 180:
        width, height = height, width
    if height <= 0 or abs(width/height-9/16) > .015:
        raise ValueError('Arka plan videosu 9:16 dikey olmalı (örneğin 1080 × 1920).')
    duration = float(stream.get('duration', info.get('format', {}).get('duration', 0)))
    if not math.isfinite(duration) or not .2 <= duration <= 600:
        raise ValueError('Video süresi 0,2 saniye ile 10 dakika arasında olmalı.')
    if duration+.001 < audio_duration:
        raise ValueError(f'Video ({duration:.1f} sn) seslendirmeden ({audio_duration:.1f} sn) kısa. En az ses kadar uzun bir video yükleyin.')
    return {'duration': duration, 'width': width, 'height': height}


def prepare(source, output, audio_duration, progress, cancelled):
    source_meta = probe(source, audio_duration)
    bitrate = str(min(8000, int(850000/source_meta['duration'])))+'k'
    progress(.1, 'Dikey video hazırlanıyor…')
    cmd = [binary('ffmpeg'), '-nostdin', '-y', '-v', 'error', '-i', str(source), '-map', '0:v:0', '-an', '-vf', 'scale=1080:1920:flags=lanczos,setsar=1,fps=30:round=up', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-maxrate', bitrate, '-bufsize', bitrate, '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)]
    with output.with_suffix('.log').open('wb') as log:
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=log)
        start = time.monotonic()
        try:
            while process.poll() is None:
                if cancelled(): raise RuntimeError('İşlem iptal edildi.')
                if time.monotonic()-start > 900: raise RuntimeError('Video hazırlama süresi aşıldı.')
                time.sleep(.2)
            if process.returncode: raise ValueError('Video dönüştürülemedi. Dosyayı MP4 olarak yeniden kaydedin.')
            meta = probe(output, audio_duration)
            if output.stat().st_size > 128*1024*1024: raise ValueError('Hazırlanan video çok büyük; daha kısa bir video yükleyin.')
            return meta
        except BaseException:
            if process.poll() is None: process.kill(); process.wait()
            output.unlink(missing_ok=True)
            raise
