import math
import re
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Style(BaseModel):
    template: Literal['dark', 'gold', 'paper', 'typewriter'] = 'dark'
    font: Literal['serif', 'sans', 'mono'] = 'serif'
    background: str = Field(default='#151719', pattern=r'^#[0-9a-fA-F]{6}$')
    foreground: str = Field(default='#F1E9D6', pattern=r'^#[0-9a-fA-F]{6}$')
    accent: str = Field(default='#D6AF70', pattern=r'^#[0-9a-fA-F]{6}$')
    font_size: int = Field(default=78, ge=30, le=130)
    line_height: float = Field(default=1.25, ge=1.0, le=1.7)
    transition: float = Field(default=.6, ge=.2, le=1.2)
    position: float = Field(default=0, ge=-.15, le=.15)
    safe_top: int = Field(default=220, ge=80, le=400)
    safe_bottom: int = Field(default=340, ge=100, le=500)
    safe_left: int = Field(default=100, ge=50, le=220)
    safe_right: int = Field(default=160, ge=50, le=260)
    grain: float = Field(default=.025, ge=0, le=.08)


class Word(BaseModel):
    text: str
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(ge=0, allow_inf_nan=False)
    confidence: float | None = None
    review: bool = False


class Sentence(BaseModel):
    id: str
    text: str = Field(min_length=1, max_length=1200)
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(gt=0, allow_inf_nan=False)
    review: bool = True
    reason: str = ''
    accent: bool = False
    words: list[Word] = Field(default_factory=list)

    @model_validator(mode='after')
    def valid(self):
        self.text = re.sub(r'\[[^\]]*\]', '', self.text).strip()
        if not self.text or self.end - self.start < .03:
            raise ValueError('Cümle boş olamaz; süresi en az 0,03 saniye olmalı.')
        return self


class Edit(BaseModel):
    name: str = Field(default='İsimsiz şiir', min_length=1, max_length=120)
    text: str = Field(default='', max_length=24000)
    sentences: list[Sentence] = Field(default_factory=list, max_length=180)
    style: Style = Field(default_factory=Style)

    @model_validator(mode='after')
    def ordered(self):
        for a, b in zip(self.sentences, self.sentences[1:]):
            if a.end > b.start + .001:
                raise ValueError('Cümle zamanları sıralı olmalı ve üst üste gelmemeli.')
        if len({s.id for s in self.sentences}) != len(self.sentences):
            raise ValueError('Cümle kimlikleri benzersiz olmalı.')
        return self


class AlignmentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=24000)
    mode: Literal['sentences', 'lines'] = 'sentences'
    model: Literal['tiny', 'base', 'small', 'medium'] = 'base'
    device: Literal['cpu', 'cuda'] = 'cpu'


class ExportRequest(Edit):
    quality: Literal['final', 'preview'] = 'final'
