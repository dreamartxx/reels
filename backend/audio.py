import json
import shutil
import subprocess
from pathlib import Path
import numpy as np


def binary(name):
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f'{name} bulunamadı. README kurulum adımlarını uygulayın.')
    return path


def probe(path: Path):
    result = subprocess.run([binary('ffprobe'), '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError('Ses dosyası okunamadı. Geçerli MP3 veya WAV yükleyin.')
    info = json.loads(result.stdout)
    audio = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
    if not audio:
        raise ValueError('Dosyada ses kanalı yok.')
    duration = float(info['format'].get('duration', audio.get('duration', 0)))
    if not .2 <= duration <= 600:
        raise ValueError('Ses uzunluğu 0,2 saniye ile 10 dakika arasında olmalı.')
    return {'duration': duration, 'sample_rate': int(audio['sample_rate']), 'channels': int(audio['channels']), 'codec': audio['codec_name']}


def prepare(path: Path, target: Path):
    subprocess.run([binary('ffmpeg'), '-nostdin', '-v', 'error', '-y', '-i', str(path), '-vn', '-ac', '1', '-ar', '16000', str(target)], check=True, capture_output=True, timeout=120)
    raw = subprocess.run([binary('ffmpeg'), '-nostdin', '-v', 'error', '-i', str(target), '-f', 'f32le', '-'], check=True, capture_output=True, timeout=30).stdout
    samples = np.frombuffer(raw, dtype=np.float32)
    bins = np.array_split(samples, min(1600, len(samples)))
    peaks = [float(np.max(np.abs(x))) for x in bins]
    maximum = max(peaks, default=1) or 1
    return [round(p / maximum, 4) for p in peaks]
