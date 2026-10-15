import json
import subprocess
from pathlib import Path
import pytest
from pydantic import ValidationError
from backend.models import Edit, Style
from backend.text import clean_text, split_poem, srt
from backend.render import motion, geometry, text_sprite, build_scene, render_frame

ROOT=Path(__file__).resolve().parents[1]


def test_tags_and_multiline_turkish():
    raw='[deep, firm]\nİnsan bir gün susuyor...\nSöylenecek çok şey var ki,\nhangisinden başlayacağını bilemiyor.\n[pause]'
    assert '[' not in clean_text(raw)
    assert split_poem(raw)==['İnsan bir gün susuyor...','Söylenecek çok şey var ki, hangisinden başlayacağını bilemiyor.']
    assert len(split_poem(raw,'lines'))==3
    with pytest.raises(ValueError):split_poem('[pause]')


def test_validation_prevents_overlap_and_nan():
    def s(start,end):return {'id':str(start),'text':'Şiir','start':start,'end':end}
    with pytest.raises(ValidationError):Edit(sentences=[s(0,2),s(1,3)])
    with pytest.raises(ValidationError):Edit(sentences=[s(float('nan'),2)])
    with pytest.raises(ValidationError):Edit(sentences=[s(0,0)])


def test_srt_carries_turkish_and_millisecond_rollover():
    assert '00:01:00,000 --> 00:01:01,250' in srt([{'text':'İyi ki…','start':59.9999,'end':61.25}])
    assert 'İyi ki…' in srt([{'text':'İyi ki…','start':0,'end':1}])


def test_motion_matches_typescript_and_is_continuous():
    sentences=[{'start':0},{'start':3},{'start':3.4},{'start':12},{'start':14}]
    times=[x/100 for x in range(1600)]
    script='import {motion} from "./frontend/src/motion.ts"; const s='+json.dumps(sentences)+';console.log(JSON.stringify('+json.dumps(times)+'.map(t=>motion(s,t,.6))));'
    output=subprocess.check_output(['node','--experimental-strip-types','--input-type=module','-e',script],cwd=ROOT,text=True)
    actual=json.loads(output)
    for t,js in zip(times,actual):
        py=motion(sentences,t,.6)
        assert len(py)<=3
        assert py==js
        assert all(0<=v['opacity']<=1 for v in py)
    # Long pause: no scrolling until the next sentence's transition window.
    assert motion(sentences,6,.6)==motion(sentences,10,.6)
    for t in [3,3.4,12,14]:
        before={x['index']:x for x in motion(sentences,t-1e-5,.6)}
        after={x['index']:x for x in motion(sentences,t+1e-5,.6)}
        for i in before.keys()&after.keys():
            assert abs(before[i]['offset']-after[i]['offset'])<.001
            assert abs(before[i]['opacity']-after[i]['opacity'])<.001


@pytest.mark.parametrize('font',['serif','sans','mono'])
def test_long_turkish_text_fits_safe_area(font):
    style=Style(font=font).model_dump(); geo=geometry(style)
    image,size=text_sprite('Çığlıklar, yağmurlar, ıssız sokaklar; içimde büyüyen bir ışık ve söylemeye fırsat bulamadığımız o iki kelime…',style,False,geo)
    assert image.width<=geo['width']
    assert image.height<=geo['max_height']
    assert image.getbbox()


def test_safe_area_for_all_visible_sentences():
    style=Style().model_dump();g=geometry(style)
    # Extreme position changes reduce spacing automatically.
    for position in [-.15,0,.15]:
        style['position']=position;g=geometry(style)
        for t in [n/100 for n in range(400)]:
            for m in motion([{'start':0},{'start':2},{'start':4}],t,.6):
                h=g['max_height']*m['scale'];y=g['y']+m['offset']*g['gap']
                assert y-h/2>=style['safe_top']
                assert y+h/2<=1920-style['safe_bottom']
