"""Pillow sprites shared by browser canvas and FFmpeg frame rendering."""
import hashlib
import json
import math
import subprocess
import unicodedata
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from .audio import binary

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1080, 1920


def motion(sentences, t, transition, duration=None):
    """Must stay identical to frontend/src/motion.ts. At most three visible items."""
    if not sentences:
        return []
    i = max(0, next((j-1 for j, s in enumerate(sentences) if s['start'] > t), len(sentences)-1))
    u = 0.
    if i + 1 < len(sentences):
        window = min(transition, (sentences[i+1]['start'] - sentences[i]['start']) * .45)
        if window > 0:
            x = max(0., min(1., (t - sentences[i+1]['start'] + window) / window))
            u = x*x*(3-2*x)
    values = [
        (i-1, -1-u, .3*max(0., 1-2*u), .72),
        (i, -u, 1-.7*u, 1-.28*u),
        (i+1, 1-u, .22+.78*u, .72+.28*u),
        (i+2, 2-u, .22*max(0., 2*u-1), .72),
    ]
    result = []
    for j, y, a, z in values:
        if not 0 <= j < len(sentences) or a <= .00001:
            continue
        phase = 0.
        if j == i-1:
            phase = .55 + .45 * max(0., min(1., (t-sentences[i]['start']) / max(.5, transition)))
        elif j == i:
            phase = .55*u
            if i == len(sentences)-1 and duration is not None:
                fade = min(max(.8, transition), max(.01, duration-sentences[i]['start']))
                phase = max(0., min(1., (t-duration+fade)/fade))
        if phase < 1:
            result.append({'index': j, 'offset': y, 'opacity': a, 'scale': z, 'dissolve': phase})
    return result


def letter_motion(index, phase):
    """Deterministic, gentle drift shared with Canvas; no frame-to-frame randomness."""
    delay = ((index*37+11) % 101)/101*.16
    p = max(0., min(1., (phase-delay)/(1-delay)))
    eased = p*p*(3-2*p)
    return {'x': (((index*73+19) % 101)/100-.5)*140*eased,
            'y': -(28+((index*43+7) % 83))*eased,
            'opacity': 1-eased}



def geometry(style):
    top, bottom = style['safe_top'], HEIGHT-style['safe_bottom']
    center_y = (top+bottom)/2 + style['position']*HEIGHT
    gap = min(center_y-top, bottom-center_y)/1.85
    return {'x': (style['safe_left']+WIDTH-style['safe_right'])/2, 'y': center_y, 'gap': gap,
            'width': WIDTH-style['safe_left']-style['safe_right'], 'max_height': gap*.94}


def wrap(text, font, max_width):
    # Handle exceptionally long tokens too, without overflowing safe margins.
    tokens = []
    for token in text.split():
        piece = ''
        for char in token:
            if piece and font.getlength(piece+char) > max_width:
                tokens.append(piece)
                piece = char
            else:
                piece += char
        if piece:
            tokens.append(piece)
    lines, line = [], ''
    for token in tokens:
        candidate = f'{line} {token}'.strip()
        if line and font.getlength(candidate) > max_width:
            lines.append(line)
            line = token
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def text_sprite(text, style, accent, geometry):
    font_path = ROOT/'assets'/'fonts'/f'{style["font"]}.ttf'
    for size in range(style['font_size'], 11, -1):
        font = ImageFont.truetype(str(font_path), size)
        lines = wrap(text, font, geometry['width']-12)
        line_step = math.ceil(size*style['line_height'])
        height = len(lines)*line_step+12
        if height <= geometry['max_height']:
            break
    else:
        raise ValueError('Bu cümle güvenli alana okunabilir boyutta sığmıyor. Cümleyi bölün veya güvenli alanı genişletin.')
    width = min(geometry['width'], math.ceil(max(font.getlength(line) for line in lines))+12)
    im = Image.new('RGBA', (int(width), height))
    draw = ImageDraw.Draw(im)
    for i, line in enumerate(lines):
        draw.text((width/2, i*line_step+6), line, font=font, fill=style['accent'] if accent else style['foreground'], anchor='mt')
    return im, size


def glyph_regions(sprite, text, style, size, geo):
    """Partition the original raster into letter cells, keeping accents attached."""
    font = ImageFont.truetype(str(ROOT/'assets/fonts'/f'{style["font"]}.ttf'), size)
    lines = wrap(text, font, geo['width']-12)
    step = math.ceil(size*style['line_height'])
    regions = []
    for row, line in enumerate(lines):
        clusters = []
        for char in line:
            if clusters and unicodedata.combining(char): clusters[-1] += char
            else: clusters.append(char)
        left = (sprite.width-font.getlength(line))/2
        prefix = ''
        y0 = 0 if row == 0 else row*step+6
        y1 = sprite.height if row == len(lines)-1 else (row+1)*step+6
        for col, char in enumerate(clusters):
            x0 = 0 if col == 0 else math.floor(left+font.getlength(prefix))
            prefix += char
            x1 = sprite.width if col == len(clusters)-1 else math.floor(left+font.getlength(prefix))
            if x1 <= x0: continue
            bbox = sprite.crop((x0,y0,x1,y1)).getbbox()
            if bbox:
                x,y,r,b = bbox
                regions.append({'x':x0+x,'y':y0+y,'width':r-x,'height':b-y})
    return regions


def background(style):
    color = np.array([int(style['background'][i:i+2], 16) for i in (1, 3, 5)], dtype=np.float32)
    y, x = np.mgrid[:HEIGHT, :WIDTH]
    radial = ((x-WIDTH/2)/(WIDTH*.8))**2 + ((y-HEIGHT/2)/(HEIGHT*.8))**2
    grain = np.random.default_rng(17).normal(0, style['grain']*255, (HEIGHT, WIDTH))
    rgb = color[None,None,:]*(1-.10*radial[:,:,None]) + grain[:,:,None]
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def build_scene(folder: Path, sentences, style):
    signature = json.dumps({'version': 2, 'text': [(s['text'], s.get('accent', False)) for s in sentences], 'style': style}, sort_keys=True)
    digest = hashlib.sha256(signature.encode()).hexdigest()[:20]
    target = folder/'scenes'/digest
    manifest_file = target/'manifest.json'
    if manifest_file.exists():
        return json.loads(manifest_file.read_text())
    target.mkdir(parents=True, exist_ok=True)
    geo = geometry(style)
    background(style).save(target/'background.jpg', quality=96)
    sprites = []
    for i, s in enumerate(sentences):
        sprite, size = text_sprite(s['text'], style, s.get('accent', False), geo)
        sprite.save(target/f'{i}.png')
        sprites.append({'file': f'{i}.png', 'width': sprite.width, 'height': sprite.height, 'font_size': size, 'glyphs': glyph_regions(sprite, s['text'], style, size, geo)})
    manifest = {'digest': digest, 'width': WIDTH, 'height': HEIGHT, 'geometry': geo, 'sprites': sprites}
    manifest_file.write_text(json.dumps(manifest), encoding='utf-8')
    return manifest


def render_frame(bg, sprites, geo, sentences, style, t, scale=1., glyphs=None, duration=None):
    frame = bg.copy()
    for item in motion(sentences, t, style['transition'], duration):
        original = sprites[item['index']]
        factor = item['scale']*scale
        left = geo['x']*scale-original.width*factor/2
        top = (geo['y']+item['offset']*geo['gap'])*scale-original.height*factor/2
        regions = glyphs[item['index']] if glyphs and item['dissolve'] > 0 else None
        pieces = regions or [{'x':0,'y':0,'width':original.width,'height':original.height}]
        for index, box in enumerate(pieces):
            drift = letter_motion(index, item['dissolve']) if regions else {'x':0,'y':0,'opacity':1}
            opacity = item['opacity']*drift['opacity']
            if opacity < .0001: continue
            x,y,w,h = (box[k] for k in ('x','y','width','height'))
            sprite = original.crop((x,y,x+w,y+h)).resize((max(1,round(w*factor)),max(1,round(h*factor))),Image.Resampling.BICUBIC)
            if opacity < .9999:
                sprite.putalpha(sprite.getchannel('A').point(lambda p:round(p*opacity)))
            frame.paste(sprite,(round(left+x*factor+drift['x']*scale),round(top+y*factor+drift['y']*scale)),sprite)
    return frame


def render_video(folder, audio, sentences, style, duration, output, preview, progress, cancelled):
    manifest = build_scene(folder, sentences, style)
    scene = folder/'scenes'/manifest['digest']
    scale = 1/3 if preview else 1
    width, height, fps = round(WIDTH*scale), round(HEIGHT*scale), 30
    bg = Image.open(scene/'background.jpg').convert('RGB').resize((width,height), Image.Resampling.LANCZOS)
    sprites = [Image.open(scene/s['file']).convert('RGBA') for s in manifest['sprites']]
    total = math.ceil(duration*fps)
    cmd = [binary('ffmpeg'), '-nostdin', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{width}x{height}', '-r', str(fps), '-i', '-', '-i', str(audio), '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19' if not preview else '24', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-t', str(duration), '-movflags', '+faststart', str(output)]
    with (output.parent/'ffmpeg.log').open('wb') as log:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log)
        try:
            for n in range(total):
                if cancelled():
                    raise RuntimeError('İşlem iptal edildi.')
                frame = render_frame(bg, sprites, manifest['geometry'], sentences, style, n/fps, scale, [s['glyphs'] for s in manifest['sprites']], duration)
                process.stdin.write(frame.tobytes())
                if n % 15 == 0:
                    progress(.02+.94*n/total, f'{n}/{total} kare oluşturuldu')
            process.stdin.close()
            code = process.wait(timeout=120)
            if code:
                raise RuntimeError('FFmpeg çıktıyı tamamlayamadı. data içindeki ffmpeg.log dosyasını kontrol edin.')
        except BaseException:
            process.kill()
            process.wait()
            output.unlink(missing_ok=True)
            raise
    progress(1, 'MP4 hazır.')
