import re


def clean_text(text: str) -> str:
    text = re.sub(r'\[[^\]]*\]', '', text)
    return '\n'.join(re.sub(r'[ \t]+', ' ', line).strip() for line in text.splitlines()).strip()


def split_poem(text: str, mode: str = 'sentences') -> list[str]:
    text = clean_text(text)
    if mode == 'lines':
        parts = [x.strip() for x in text.splitlines() if x.strip()]
    else:
        # A single line break is not a sentence boundary; blank lines mark stanzas.
        parts = []
        for stanza in re.split(r'\n\s*\n', text):
            stanza = re.sub(r'\s+', ' ', stanza).strip()
            parts.extend(x.strip() for x in re.split(r'(?<=[.!?…])\s+', stanza) if x.strip())
    if not parts:
        raise ValueError('Performans etiketleri dışında bir şiir metni girin.')
    if len(parts) > 180 or any(len(p) > 1200 for p in parts):
        raise ValueError('En fazla 180 cümle; cümle başına 1200 karakter desteklenir. Uzun metni kıtalara ayırın.')
    return parts


def srt(sentences) -> str:
    def stamp(t):
        ms = round(t * 1000)
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f'{h:02}:{m:02}:{s:02},{ms:03}'
    return '\n\n'.join(f'{i+1}\n{stamp(s["start"])} --> {stamp(s["end"])}\n{s["text"]}' for i, s in enumerate(sentences)) + '\n'
