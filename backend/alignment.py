"""Forced alignment only: the supplied poem is never replaced by ASR text."""
import os
import re
import unicodedata
from pathlib import Path
from .models import Sentence, Word
from .text import split_poem
from .audio import probe

_MODELS = {}


def key(text):
    return re.sub(r'[^\w]', '', unicodedata.normalize('NFC', text).casefold().replace('ı', 'i').replace('i\u0307', 'i'))


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
    duration = probe(audio)['duration']
    expected = ''.join(key(p) for p in parts)
    words = []
    # A larger token window can recover tokenizer boundary drift. Never repair
    # missing text by inventing timings or substituting a transcription.
    for attempt, token_step in enumerate((100, 400)):
        message = ('Türkçe metin sesle kelime düzeyinde eşleştiriliyor…' if attempt == 0
                   else 'Kelime sınırları daha geniş metin aralığıyla yeniden eşleştiriliyor…')
        base, weight = (.12, .38) if attempt == 0 else (.52, .44)
        progress(base, message)
        result = _MODELS[cache_key].align(
            str(audio), '\n'.join(parts), language='tr', original_split=True,
            regroup=False, verbose=None, suppress_silence=True, token_step=token_step,
            progress_callback=lambda done, total: progress(base + weight * min(1, done / max(total, .01)), message),
        )
        if result is None:
            words = []
        else:
            words = [w for segment in result.to_dict()['segments'] for w in segment.get('words', [])]
        if words and expected == ''.join(key(w['word']) for w in words):
            break
    sentences = map_words(parts, words, duration)
    progress(1, 'Hizalama tamamlandı.')
    return sentences


def map_words(parts, words, duration):
    """Validate coverage before converting model output to editable sentences."""
    if not words:
        raise ValueError('Metin sesle eşleştirilemedi. Metnin seslendirmeyle aynı olduğunu kontrol edin.')
    # stable-ts may append unaligned words with start=end=audio duration.
    # These placeholders must not become fabricated .04-second sentences.
    tail = len(words)
    while tail and (abs(float(words[tail-1]['start']) - duration) <= .04
                    and abs(float(words[tail-1]['end']) - float(words[tail-1]['start'])) <= .000001):
        tail -= 1
    if tail < len(words):
        excerpt = ' '.join(w['word'].strip() for w in words[tail:tail+5])
        minutes, seconds = divmod(duration, 60)
        raise ValueError(
            f'Sesin sonuna ulaşıldı ({int(minutes):02}:{seconds:04.1f}). '
            f'Metnin sonundaki {len(words)-tail} kelimeye zaman atanamadı; başlangıç: “{excerpt}”. '
            'Ses kaydı ile metnin aynı yerde bittiğini kontrol edin. Kayıt eksikse tam ses dosyasını yükleyin; '
            'yalnızca bu kesiti kullanacaksanız metni kayıtta okunan bölümle sınırlandırın. Metniniz değiştirilmedi.'
        )
    expected = ''.join(key(p) for p in parts)
    actual = ''.join(key(w['word']) for w in words)
    if expected != actual:
        raise ValueError('İki hizalama denemesinde de bazı kelimeler eşleştirilemedi. Ses ile metnin aynı olduğunu kontrol edin veya daha hassas bir model seçin. Metniniz değiştirilmedi.')
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
            word_duration = float(w['end']) - float(w['start'])
            flagged = word_duration < .04 or word_duration > 2.5 or confidence is None or confidence < .45
            mapped.append(Word(text=w['word'].strip(), start=max(0, w['start']), end=max(0, w['end']), confidence=confidence, review=flagged))
        start = max(previous_end, float(ws[0]['start']))
        end = max(start + .04, float(ws[-1]['end']))
        if end > duration + .001:
            raise ValueError(f'{i+1}. cümle sesin sonuna sığmıyor. Tam ses kaydını yükleyin veya metni okunan bölüme göre düzenleyin. Metniniz değiştirilmedi.')
        flagged = any(w.review for w in mapped) or start != float(ws[0]['start'])
        reason = 'Düşük güven / sıra dışı kelime süresi. Dinleyerek kontrol edin.' if flagged else ''
        sentences.append(Sentence(id=f's{i+1}', text=part, start=start, end=end, review=flagged, reason=reason, words=mapped).model_dump())
        previous_end = end
    return sentences
