import sys
from types import SimpleNamespace
from copy import deepcopy
from pathlib import Path
import pytest
from backend import alignment


def word(text,start,end):
    return dict(word=text,start=start,end=end,probability=.9)


def test_end_of_audio_placeholders_report_missing_tail_without_fake_times():
    parts=['Bugünden vazgeçme.','Henüz son sayfaya gelmedin.']
    words=[word('Bugünden',0,.5),word('vazgeçme.',.5,1)]
    words += [word(w,1.2,1.2) for w in ['Henüz','son','sayfaya','gelmedin.']]
    before=deepcopy(words)
    with pytest.raises(ValueError,match='sonundaki 4 kelime') as error:
        alignment.map_words(parts,words,1.2)
    assert 'Henüz son sayfaya gelmedin.' in str(error.value)
    assert 'Metniniz değiştirilmedi' in str(error.value)
    assert words==before


def test_original_turkish_text_and_split_token_spans_preserved():
    parts=['İyi ki…',"Ankara'da bir gün."]
    words=[word('İyi',0,.3),word('ki…',.3,.5),word('Ankara',1,1.3),word("'da",1.3,1.4),word('bir',1.4,1.6),word('gün.',1.6,1.9)]
    result=alignment.map_words(parts,words,2)
    assert [s['text'] for s in result]==parts
    assert result[1]['start']==1 and result[1]['end']==1.9
    assert alignment.key('İÇİN')==alignment.key('için')
    assert alignment.key('yağmur')==alignment.key('yag\u0306mur')


def test_token_window_retry_preserves_text_instead_of_inventing_missing_word(monkeypatch):
    calls=[]
    def align(*args,**kwargs):
        calls.append(kwargs['token_step'])
        words=[word('İyi',0,.3)] if len(calls)==1 else [word('İyi',0,.3),word('ki.',.3,.6)]
        return SimpleNamespace(to_dict=lambda:{'segments':[{'words':words}]})
    model=SimpleNamespace(align=align)
    monkeypatch.setitem(sys.modules,'stable_whisper',SimpleNamespace(load_model=lambda *a,**kw:model))
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(set_num_threads=lambda n:None,cuda=SimpleNamespace(is_available=lambda:False)))
    monkeypatch.setattr(alignment,'_MODELS',{})
    monkeypatch.setattr(alignment,'probe',lambda _:dict(duration=1))
    out=alignment.align(Path('test.wav'),'İyi ki.','sentences','base','cpu',Path('.'),lambda *args:None)
    assert calls==[100,400]
    assert out[0]['text']=='İyi ki.' and out[0]['end']==.6


def test_zero_time_sentence_cannot_extend_past_audio():
    with pytest.raises(ValueError,match='sesin sonuna sığmıyor'):
        alignment.map_words(['İyi ki.'],[word('İyi',.99,.995),word('ki.',.995,1)],1)
