"""Forced alignment only: the supplied poem is never replaced by ASR text."""
import os
import re
from pathlib import Path
from .models import Sentence, Word
from .text import split_poem

_MODELS = {}


def key(text):
    return re.sub(r'[^\w]', '', text.casefold().replace('ı', 'i').replace('i\u0307', 'i'))


def align(audio: Path, text: str, mode: str, model_name: str, device: str, model_dir: Path, progress):
    import stable_whisper
    import torch
    if device == 'cuda' and not torch.cuda.is_available():
        raise ValueError('CUDA destekli GPU bulunamadı. CPU seçin.')
    torch.set_num_threads(min(6, os.cpu_count() or 2))
    parts = split_poem(text, mode)
    progress(.03, f'{model_name} modeli hazırlanıyor; ilk kullanımda model indirilir.')
    cache_key = (model_name, device)
    if cache_key not in _MODELS:
        # Keep at most one model in memory.
        _MODELS.clear()
        _MODELS[cache_key] = stable_whisper.load_model(model_name, device=device, download_root=str(model_dir))
    progress(.12, 'Türkçe metin sesle kelime düzeyinde eşleştiriliyor…')
    result = _MODELS[cache_key].align(
        str(audio), '\n'.join(parts), language='tr', original_split=True,
        regroup=False, verbose=None, suppress_silence=True,
        progress_callback=lambda done, total: progress(.12 + .82 * min(1, done / max(total, .01)), 'Kelime zamanları hesaplanıyor…'),
    )
    if result is None:
        raise ValueError('Metin sesle eşleştirilemedi. Metnin seslendirmeyle aynı olduğunu kontrol edin.')
    data = result.to_dict()
    words = [w for s in data['segments'] for w in s.get('words', [])]
    # Match character spans, not whitespace counts: tokenizer can split punctuation
    # and apostrophes differently, while the original poem stays untouched.
    expected = ''.join(key(p) for p in parts)
    actual = ''.join(key(w['word']) for w in words)
    if expected != actual:
        raise ValueError('Hizalama motoru verilen metnin tüm kelimelerini koruyamadı. Metni kontrol edip yeniden deneyin; elle zamanlama da kullanılabilir.')
    spans, cursor = [], 0
    for w in words:
        n = len(key(w['word']))
        if n:
            spans.append((cursor, cursor+n, w))
        cursor += n
    sentences, cursor, previous_end = [], 0, 0.
    for i, part in enumerate(parts):
        end_cursor = cursor + len(key(part))
        ws = [w for a, b, w in spans if b > cursor and a < end_cursor]
        cursor = end_cursor
        if not ws:
            raise ValueError(f'{i+1}. cümle için kelime zamanı bulunamadı.')
        mapped = []
        for w in ws:
            confidence = w.get('probability')
            duration = float(w['end']) - float(w['start'])
            flagged = duration < .04 or duration > 2.5 or confidence is None or confidence < .45
            mapped.append(Word(text=w['word'].strip(), start=max(0, w['start']), end=max(0, w['end']), confidence=confidence, review=flagged))
        start = max(previous_end, float(ws[0]['start']))
        end = max(start + .04, float(ws[-1]['end']))
        flagged = any(w.review for w in mapped) or start != float(ws[0]['start'])
        reason = 'Düşük güven / sıra dışı kelime süresi. Dinleyerek kontrol edin.' if flagged else ''
        sentences.append(Sentence(id=f's{i+1}', text=part, start=start, end=end, review=flagged, reason=reason, words=mapped).model_dump())
        previous_end = end
    progress(1, 'Hizalama tamamlandı.')
    return sentences
