"""Portable, stable download names for each render."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo


def download_name(name: str, created_at: float, job_id: str, filename: str) -> str:
    name = name.translate(str.maketrans('ÇĞİÖŞÜçğıöşü', 'CGIOSUcgiosu')).lower()
    slug = re.sub('[^a-z0-9]+', '-', name).strip('-')[:80].rstrip('-') or 'reels'
    stamp = datetime.fromtimestamp(created_at, ZoneInfo('Europe/Istanbul')).strftime('%Y%m%d-%H%M%S')
    extension = filename.rsplit('.', 1)[-1]
    return f'{slug}_{stamp}_{job_id[:12]}.{extension}'
