#!/usr/bin/env python3
"""
Nitrato · generador de reels (1080x1920, 24 fps).

Uso:
    python3 reels/nitrato_reel.py guion.json            # vídeo completo
    python3 reels/nitrato_reel.py guion.json 3 9.5 20   # fotogramas de prueba (PNG) en esos segundos

El guion es un JSON con la lista de escenas. Ver reels/README.md y reels/ejemplos/.
Requiere: Python 3 con Pillow y NumPy, y ffmpeg.
"""
import hashlib, json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fuentes")
W, H, FPS = 1080, 1920, 24
BASE = (29, 19, 16); EDGE = (13, 8, 7); HOLE = (59, 42, 33)
INK = (236, 220, 194); MUTED = (179, 157, 132); AMBER = (234, 162, 58)
ML, MR = 140, 160                 # márgenes: bandas de película y botones de Instagram
TW = W - ML - MR
COLORS = {"tinta": INK, "ambar": AMBER, "gris": MUTED}

# ---------------------------------------------------------------- tipografía
_fc = {}
def bs(size, wght=800):
    k = ("bs", size, wght)
    if k not in _fc:
        f = ImageFont.truetype(os.path.join(FONTS, "BigShouldersDisplay.ttf"), size)
        try: f.set_variation_by_axes([wght])
        except Exception: pass
        _fc[k] = f
    return _fc[k]
def sp(size, style="Regular"):
    k = ("sp", size, style)
    if k not in _fc: _fc[k] = ImageFont.truetype(os.path.join(FONTS, f"Spectral-{style}.ttf"), size)
    return _fc[k]

def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def clamp(x): return max(0.0, min(1.0, x))
def fade_out(t, dur, length=0.45): return clamp((dur - t) / length)

def wrap(text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.getlength(test.replace("*", "")) <= width: cur = test
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def line_img(line, font, color=INK, accent=AMBER, track=0):
    """Una línea como imagen; las palabras entre *asteriscos* van en ámbar."""
    asc, desc = font.getmetrics()
    w = int(font.getlength(line.replace("*", "")) + track * len(line)) + 8
    im = Image.new("RGBA", (max(w, 1), asc + desc + 6), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x, hot = 0, False
    for ch in line:
        if ch == "*": hot = not hot; continue
        d.text((x, 0), ch, font=font, fill=accent if hot else color)
        x += font.getlength(ch) + track
    return im

def block(text, font, color=INK, lead=1.0, track=0, width=TW):
    out, hot = [], False
    for ln in wrap(text, font, width):
        s = ("*" if hot else "") + ln
        if s.count("*") % 2: s += "*"; hot = True
        else: hot = False
        out.append(line_img(s, font, color, track=track))
    return out, int(font.size * lead)

def place(canvas, lines, lh, x, y, t, start, stagger=0.2, dur=0.6, alpha=1.0, rise=40):
    for i, im in enumerate(lines):
        p = ease((t - start - i * stagger) / dur)
        if p <= 0: continue
        a = im.copy()
        if p < 1 or alpha < 1: a.putalpha(a.getchannel("A").point(lambda v: int(v * p * alpha)))
        canvas.alpha_composite(a, (int(x), int(y + i * lh + (1 - p) * rise)))
    return y + len(lines) * lh

# estilos de texto: (fuente, color, interlineado, en mayúsculas)
def style(name, size=None):
    if name == "titular":   return bs(size or 96), INK, 1.0, True
    if name == "grande":    return bs(size or 140), INK, 0.95, True
    if name == "cuerpo":    return sp(size or 54, "Regular"), INK, 1.28, False
    if name == "cursiva":   return sp(size or 62, "Italic"), INK, 1.22, False
    if name == "destacado": return sp(size or 72, "Italic"), AMBER, 1.2, False
    if name == "cita":      return sp(size or 68, "Italic"), INK, 1.25, False
    if name == "pie":       return sp(size or 46, "Italic"), MUTED, 1.25, False
    raise ValueError(f"estilo desconocido: {name}")

# ---------------------------------------------------------------- material (imágenes y vídeo)
def grade(im, warm=0.1, sat=0.85, con=1.05):
    im = ImageEnhance.Color(im).enhance(sat); im = ImageEnhance.Contrast(im).enhance(con)
    a = np.asarray(im).astype(np.float32)
    a[..., 0] *= 1 + warm; a[..., 1] *= 1 + warm * 0.35; a[..., 2] *= 1 - warm * 0.6
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def cover(im, zoom=1.0, fx=0.5, fy=0.5):
    s = max(W / im.width, H / im.height) * zoom
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    x = int((im.width - W) * fx); y = int((im.height - H) * fy)
    return im.crop((x, y, x + W, y + H))

def framed(im, box_w, zoom=1.0, y=None):
    """Imagen encajada a un ancho, sobre una versión ampliada y desenfocada de sí misma."""
    bg = ImageEnhance.Brightness(cover(im).filter(ImageFilter.GaussianBlur(40))).enhance(0.45)
    s = box_w / im.width * zoom
    fg = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    cy = y if y is not None else H // 2
    bg.paste(fg, (W // 2 - fg.width // 2, int(cy - fg.height // 2)))
    return bg

def lerp2(v, k):
    if isinstance(v, (list, tuple)): return v[0] + (v[1] - v[0]) * k
    return v

class Media:
    """Fondo de una escena: imagen fija o fragmento de vídeo."""
    def __init__(self, spec, dur, base_dir, cache):
        self.spec, self.dur = spec, dur
        self.frames, self.still = None, None
        if "imagen" in spec:
            self.still = grade(Image.open(os.path.join(base_dir, spec["imagen"])).convert("RGB"), warm=0.07)
        elif "video" in spec:
            src = os.path.join(base_dir, spec["video"])
            key = hashlib.md5(json.dumps(spec, sort_keys=True).encode() + str(dur).encode()).hexdigest()[:12]
            out = os.path.join(cache, key); os.makedirs(out, exist_ok=True)
            if not os.listdir(out):
                slow = float(spec.get("lento", 1.0))
                pre = (spec["recorte"] + ",") if spec.get("recorte") else ""   # ffmpeg crop=w:h:x:y para quitar bandas negras
                modo = spec.get("modo", "vertical")
                if modo == "vertical":
                    fx = spec.get("centro_x", 0.5)
                    vf = (f"{pre}setpts={slow}*PTS,crop='min(iw,ih*9/16)':ih:'(iw-min(iw,ih*9/16))*{fx}':0,"
                          f"scale={W}:{H}:flags=lanczos,fps={FPS}")
                    cmd = ["-vf", vf]
                else:  # enmarcado
                    wpx = int(spec.get("ancho", 1400)); dy = int(spec.get("desplaza_y", -120))
                    fc = (f"[0]{pre}setpts={slow}*PTS,split[a][b];[a]scale=-2:{H},crop={W}:{H},boxblur=30:2,eq=brightness=-0.22[bg];"
                          f"[b]scale={wpx}:-2,crop='min(iw,{W})':ih[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2+{dy},fps={FPS}")
                    cmd = ["-filter_complex", fc]
                need = dur / slow + 0.2
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(spec.get("desde", 0)), "-t", str(need), "-i", src]
                               + cmd + ["-q:v", "3", os.path.join(out, "%05d.jpg")], check=True)
            self.frames = sorted(os.path.join(out, f) for f in os.listdir(out))

    def frame(self, t):
        k = clamp(t / max(self.dur, 0.01)); s = self.spec
        if self.frames:
            im = Image.open(self.frames[min(len(self.frames) - 1, int(t * FPS))]).convert("RGB")
            return grade(im, warm=0.12)
        if s.get("modo", "vertical") == "enmarcado":
            return framed(self.still, int(s.get("ancho", 900)), zoom=lerp2(s.get("zoom", [1.0, 1.05]), k), y=s.get("y", 880))
        return cover(self.still, lerp2(s.get("zoom", [1.0, 1.06]), k), fx=lerp2(s.get("centro_x", 0.5), k), fy=lerp2(s.get("centro_y", 0.5), k))

def shade(c, y0, y1, strength=0.8):
    g = Image.new("L", (1, H), 0); px = g.load()
    for y in range(H):
        v = 1.0 if y0 <= y <= y1 else clamp(1 - (y0 - y) / 260) if y < y0 else clamp(1 - (y - y1) / 260)
        px[0, y] = int(255 * strength * v ** 1.4)
    dark = Image.new("RGBA", (W, H), (14, 9, 7, 255)); dark.putalpha(g.resize((W, H))); c.alpha_composite(dark)

# ---------------------------------------------------------------- escenas
POS = {"arriba": 360, "centro": 700, "abajo": 1150}

def draw_texts(c, scene, t, dur, has_bg):
    a = fade_out(t, dur)
    y = POS.get(scene.get("pos", "abajo" if has_bg else "arriba"), 1150)
    if isinstance(scene.get("pos"), (int, float)): y = scene["pos"]
    if scene.get("antetitulo"):
        place(c, [line_img(scene["antetitulo"], bs(38, 600), AMBER, track=6)], 0, ML, y - 60, t, 0.0, alpha=a)
    for i, tx in enumerate(scene.get("textos", [])):
        f, colr, lead, upper = style(tx.get("estilo", "cursiva"), tx.get("tam"))
        colr = COLORS.get(tx.get("color"), colr)
        txt = tx["texto"].upper() if upper else tx["texto"]
        x = ML + (50 if tx.get("estilo") == "cita" else 0)
        width = TW - (50 if tx.get("estilo") == "cita" else 0)
        L, lh = block(txt, f, colr, lead=lead, width=width)
        start = tx.get("desde", 0.2 + i * 1.2)
        y0 = y
        y = place(c, L, lh, x, y, t, start, stagger=0.22, alpha=a) + tx.get("espacio", 30)
        if tx.get("estilo") == "cita":
            h = (y - 30 - y0) * ease((t - start + 0.1) / 1.2)
            ImageDraw.Draw(c).rectangle([ML, y0 + 12, ML + 8, y0 + 12 + h], fill=AMBER + (int(255 * a),))
    return y

def ficha(c, scene, t, dur):
    a = fade_out(t, dur); d = ImageDraw.Draw(c); p = ease(t / 0.8)
    d.line([(ML, 560), (ML + TW * p, 560)], fill=AMBER + (int(255 * a),), width=3)
    L, lh = block(scene["titulo"].upper(), bs(scene.get("tam", 132)), lead=0.95)
    y = place(c, L, lh, ML, 600, t, 0.15, alpha=a) + 50
    for i, (k, v) in enumerate(scene.get("filas", [])):
        st = 0.7 + i * 0.22
        place(c, [line_img(k.upper(), bs(34, 600), MUTED, track=4)], 0, ML, y + 14, t, st, alpha=a, rise=20)
        place(c, [line_img(v, sp(54), INK)], 0, ML + 250, y, t, st, alpha=a, rise=20)
        d.line([(ML, y + 84), (ML + TW * ease((t - st) / 0.6), y + 84)], fill=(234, 162, 58, int(70 * a * clamp((t - st) / 0.6))), width=1)
        y += 92

def cierre(c, scene, t, dur):
    title = line_img("NITRATO", bs(250, 800), AMBER, track=8)
    place(c, [title], 0, (W - title.width) / 2, 560, t, 0.1, rise=0)
    rows = [("Artículo completo en", sp(54, "Italic"), INK), ("nitratogarces.github.io", sp(58, "SemiBold"), INK), ("ENLACE EN LA BIO", bs(40, 600), AMBER)]
    for i, (txt, f, col) in enumerate(rows):
        im = line_img(txt, f, col, track=4 if i == 2 else 0)
        place(c, [im], 0, (W - im.width) / 2, 900 + i * 92 + (30 if i == 2 else 0), t, 0.7 + i * 0.25, rise=20)

def render_scene(c, scene, media, t, dur):
    kind = scene.get("tipo", "texto")
    if kind == "cierre": return cierre(c, scene, t, dur)
    if kind == "ficha" and media is None: return ficha(c, scene, t, dur)
    has_bg = media is not None
    if has_bg:
        fr = media.frame(t)
        blur = scene.get("desenfoque")          # [inicio, duración] en segundos de la escena
        bk = 0.0
        if blur:
            bk = clamp((t - blur[0]) / blur[1]) ** 1.4
            if bk > 0.01: fr = fr.filter(ImageFilter.GaussianBlur(20 * bk))
        c.alpha_composite(fr.convert("RGBA"))
        pos = scene.get("pos", "abajo"); y = POS.get(pos, pos if isinstance(pos, (int, float)) else 1150)
        shade(c, y - 80, y + scene.get("alto_sombra", 420), scene.get("sombra", 0.85))
        if blur and bk > 0.01:
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); draw_texts(layer, {**scene, "textos": scene.get("textos", [])[:1]}, t, dur, True)
            layer = layer.filter(ImageFilter.GaussianBlur(24 * bk))
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * (1 - 0.5 * bk)))); c.alpha_composite(layer)
            rest = scene.get("textos", [])[1:]
            if rest: draw_texts(c, {**scene, "antetitulo": None, "textos": rest, "pos": scene.get("pos2", 1250)}, t, dur, True)
            return
    draw_texts(c, scene, t, dur, has_bg)

# ---------------------------------------------------------------- película
def _edge_text():
    return line_img("NITRATE FILM  ·  NITRATO  ·  ", bs(26, 600), AMBER, track=8).rotate(-90, expand=True)

class Film:
    def __init__(self):
        rng = np.random.default_rng(7)
        self.grain = [(rng.normal(0, 1, (H // 2, W // 2)) * 11).astype(np.float32) for _ in range(6)]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        v = 1 - 0.55 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.46) / (H * 0.62)) ** 2)
        self.vign = np.clip(v, 0.25, 1)[..., None]; self.edge = _edge_text()
        et = self.edge.copy(); et.putalpha(et.getchannel("A").point(lambda v: int(v * 0.55))); self.edge = et

    def frame(self, content, fi, rnd):
        c = Image.new("RGBA", (W, H), BASE + (255,))
        dx = int(round(1.6 * math.sin(fi * 0.37) + rnd.uniform(-0.8, 0.8))); dy = int(round(1.2 * math.sin(fi * 0.23)))
        c.alpha_composite(content, (dx, dy)); d = ImageDraw.Draw(c)
        off = (fi * 9) % 64
        for side in (0, W - 62):
            d.rectangle([side, 0, side + 62, H], fill=EDGE + (255,))
            hx = side + (12 if side == 0 else 26)
            for y in range(-64 + off, H, 64): d.rounded_rectangle([hx, y, hx + 24, y + 34], radius=5, fill=HOLE + (255,))
        eh = self.edge.height
        for y in range(-eh + (fi * 9) % eh, H, eh): c.alpha_composite(self.edge, (40, y))
        if rnd.random() < 0.35:
            x = rnd.randint(ML, W - MR); d.line([(x, 0), (x + rnd.randint(-6, 6), H)], fill=(236, 220, 194, rnd.randint(30, 80)), width=rnd.choice([1, 2]))
        for _ in range(rnd.randint(0, 4)):
            x, y, r = rnd.randint(70, W - 70), rnd.randint(0, H), rnd.uniform(1.5, 4.5)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(10, 6, 5, 200) if rnd.random() < .6 else (236, 220, 194, 120))
        arr = np.asarray(c.convert("RGB")).astype(np.float32)
        g = np.repeat(np.repeat(self.grain[fi % 6], 2, 0), 2, 1)[..., None]
        return np.clip(arr * self.vign * (1 + rnd.uniform(-0.035, 0.035)) + g, 0, 255).astype(np.uint8)

# ---------------------------------------------------------------- principal
def main(spec_path, preview=None):
    spec = json.load(open(spec_path)); base_dir = os.path.dirname(os.path.abspath(spec_path))
    cache = os.path.join(base_dir, ".cache_reel"); os.makedirs(cache, exist_ok=True)
    scenes = spec["escenas"]
    for s in scenes:
        if s.get("tipo") == "cierre": s.setdefault("dur", 5.2)
    medias = [Media(s["fondo"], s["dur"], base_dir, cache) if s.get("fondo") else None for s in scenes]
    total = sum(s["dur"] for s in scenes); n = int(total * FPS)
    out = os.path.join(base_dir, spec.get("salida", "reel.mp4"))
    film, rnd = Film(), random.Random(3)
    if preview is None:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                               "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest", "-c:v", "libx264", "-preset", "veryfast",
                               "-crf", "23", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
                               "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    frames = range(n) if preview is None else [int(p * FPS) for p in preview]
    for fi in frames:
        tt = fi / FPS; acc = 0; idx = 0
        for idx, s in enumerate(scenes):
            if tt < acc + s["dur"] or idx == len(scenes) - 1: break
            acc += s["dur"]
        s, t = scenes[idx], tt - acc
        content = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        render_scene(content, s, medias[idx], t, s["dur"])
        last = idx == len(scenes) - 1
        k = min(clamp(t / 0.25) if idx > 0 else 1, clamp((total - tt) / 0.6) if last else clamp((s["dur"] - t) / 0.25))
        if medias[idx] is None and not last: k = 1 if idx == 0 else clamp(t / 0.25)
        if k < 1: content.putalpha(content.getchannel("A").point(lambda v: int(v * k)))
        if 0 <= t < 0.2 and idx > 0:
            content.alpha_composite(Image.new("RGBA", (W, H), AMBER + (int(80 * (1 - t / 0.2)),)))
        frame = film.frame(content, fi, rnd)
        if preview is None: ff.stdin.write(frame.tobytes())
        else: Image.fromarray(frame).save(os.path.join(base_dir, f"prueba_{tt:05.1f}.png"))
    if preview is None:
        ff.stdin.close(); ff.wait(); print(f"Hecho: {out} ({total:.1f} s)")

if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    main(sys.argv[1], [float(x) for x in sys.argv[2:]] or None)
