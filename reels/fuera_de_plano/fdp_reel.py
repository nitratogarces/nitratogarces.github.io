#!/usr/bin/env python3
"""
Fuera de Plano · generador de reels (1080x1920, 24 fps), con la estética de las láminas:
negro cálido, marco fino dorado con esquinas en escuadra, versalitas espaciadas, Spectral,
firma «Miguel Garcés» y contador de lámina.

Uso:
    python3 fdp_reel.py guion.json            # vídeo completo
    python3 fdp_reel.py guion.json 3 9.5 20   # fotogramas de prueba (PNG)
"""
import hashlib, json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = next((p for p in (os.path.join(HERE, "fuentes"), os.path.join(HERE, "..", "fuentes")) if os.path.isdir(p)), "fuentes")
W, H, FPS = 1080, 1920, 24
BG = (18, 18, 16); CREAM = (236, 230, 216); GOLD = (201, 164, 92); GOLD_L = (222, 192, 130)
MUTED = (128, 124, 116); GRID = (255, 255, 255)
X0, X1 = 150, 930                     # columna de texto
FR = (64, 150, 1016, 1600)            # marco (deja libre la zona de los botones de Instagram)
COLORS = {"crema": CREAM, "oro": GOLD_L, "gris": MUTED}

_fc = {}
def sp(size, style="Regular"):
    k = (size, style)
    if k not in _fc: _fc[k] = ImageFont.truetype(os.path.join(FONTS, f"Spectral-{style}.ttf"), size)
    return _fc[k]

def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3
def lerp(a, b, k): return a + (b - a) * k
def lerp2(v, k): return lerp(v[0], v[1], k) if isinstance(v, (list, tuple)) else v
def rgba(c, a): return tuple(c[:3]) + (int(255 * clamp(a)),)

def caps(d, xy, text, size, color, a, track=0.32, anchor_right=False):
    """Versalitas espaciadas, como los rótulos de las láminas."""
    f = sp(size, "SemiBold"); text = text.upper(); sp_px = size * track
    width = sum(f.getlength(ch) for ch in text) + sp_px * (len(text) - 1)
    x, y = xy
    if anchor_right: x -= width
    for ch in text:
        d.text((x, y), ch, font=f, fill=rgba(color, a)); x += f.getlength(ch) + sp_px
    return width

# ------------------------------------------------ texto enriquecido: *cursiva dorada*
def tokens(text, base_style):
    out, hot, prev_open = [], False, False
    for part in text.split("*"):
        for j, w in enumerate(part.split(" ")):
            # pegado a la anterior si no hay espacio entre ambas (p. ej. «Bushido*:»)
            if w: out.append((w, hot, j == 0 and prev_open and bool(out)))
        prev_open = bool(part) and not part.endswith(" ")
        hot = not hot
    return out

def layout(text, size, style, color, width):
    f_base = sp(size, style); f_hot = sp(size, "Italic")
    lines, cur, cw = [], [], 0
    space = f_base.getlength(" ")
    for w, hot, glue in tokens(text, style):
        f = f_hot if hot else f_base; lw = f.getlength(w)
        if cur and not glue and cw + space + lw > width: lines.append(cur); cur, cw = [], 0
        cur.append((w, hot, glue)); cw += (space if cw and not glue else 0) + lw
    if cur: lines.append(cur)
    imgs = []
    for ln in lines:
        asc, desc = f_base.getmetrics()
        im = Image.new("RGBA", (int(width + 40), asc + desc + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 0
        for i, (w, hot, glue) in enumerate(ln):
            f = f_hot if hot else f_base
            if glue and i > 0: x -= space
            d.text((x, 0), w, font=f, fill=GOLD_L if hot else color); x += f.getlength(w) + space
        imgs.append(im)
    return imgs

STYLES = {  # tamaño, estilo, color, interlineado
    "titulo":    (118, "Italic", CREAM, 1.0),
    "cuerpo":    (52, "Regular", CREAM, 1.34),
    "suave":     (48, "Regular", (200, 194, 180), 1.34),
    "cursiva":   (54, "Italic", CREAM, 1.38),
    "dialogo":   (52, "Regular", CREAM, 1.0),
    "numero":    (250, "Italic", GOLD_L, 1.0),
}

def place(c, imgs, lh, x, y, t, start, stagger=0.18, dur=0.7, alpha=1.0, rise=24):
    for i, im in enumerate(imgs):
        p = ease((t - start - i * stagger) / dur)
        if p <= 0: continue
        a = im.copy(); a.putalpha(a.getchannel("A").point(lambda v: int(v * p * alpha)))
        c.alpha_composite(a, (int(x), int(y + i * lh + (1 - p) * rise)))
    return y + len(imgs) * lh

# ------------------------------------------------ material
def grade(im, sat=0.9, con=1.04):
    return ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(sat)).enhance(con)

def fit(im, w, h, zoom=1.0, fx=0.5, fy=0.5):
    s = max(w / im.width, h / im.height) * zoom
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    x = int((im.width - w) * fx); y = int((im.height - h) * fy)
    return im.crop((x, y, x + w, y + h))

class Medium:
    def __init__(self, spec, dur, base_dir, cache):
        self.s, self.dur = spec, dur; self.frames = None; self.still = None
        if "imagen" in spec:
            self.still = grade(Image.open(os.path.join(base_dir, spec["imagen"])).convert("RGB"))
        else:
            key = hashlib.md5((json.dumps(spec, sort_keys=True) + str(dur)).encode()).hexdigest()[:12]
            out = os.path.join(cache, key); os.makedirs(out, exist_ok=True)
            if not os.listdir(out):
                parts = spec.get("tramos") or [[spec.get("desde", 0), spec.get("desde", 0) + dur / spec.get("lento", 1.0) + 0.2]]
                slow = spec.get("lento", 1.0)
                for j, (a, b) in enumerate(parts):
                    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(a), "-t", str(b - a), "-i", os.path.join(base_dir, spec["video"]),
                                    "-vf", f"setpts={slow}*PTS,fps={FPS},scale=1280:-2:flags=lanczos", "-q:v", "2",
                                    os.path.join(out, f"p{j}_%05d.jpg")], check=True)
            self.frames = sorted(os.path.join(out, f) for f in os.listdir(out))

    def frame(self, t, w, h):
        k = clamp(t / max(self.dur, 0.01)); s = self.s
        if self.frames:
            im = grade(Image.open(self.frames[min(len(self.frames) - 1, int(t * FPS))]).convert("RGB"))
        else: im = self.still
        return fit(im, w, h, lerp2(s.get("zoom", [1.0, 1.05]), k), lerp2(s.get("foco_x", 0.5), k), lerp2(s.get("foco_y", 0.5), k))

# ------------------------------------------------ lámina
def chrome(c, firma, num, total, a=1.0, grid=False):
    d = ImageDraw.Draw(c)
    x0, y0, x1, y1 = FR
    if grid:
        for gx in range(540, x1, 54): d.line([(gx, y0), (gx, y1)], fill=rgba(GRID, 0.025))
        for gy in range(y0, y1, 54): d.line([(540, gy), (x1, gy)], fill=rgba(GRID, 0.025))
        d.line([(540, y0), (540, y1)], fill=rgba(GOLD, 0.25))
    d.rectangle([x0, y0, x1, y1], outline=rgba(GOLD, 0.45), width=1)
    L = 46
    d.line([(x0 - 10, y0 - 10), (x0 - 10 + L, y0 - 10)], fill=rgba(GOLD, 0.9), width=3)
    d.line([(x0 - 10, y0 - 10), (x0 - 10, y0 - 10 + L)], fill=rgba(GOLD, 0.9), width=3)
    d.line([(x1 + 10, y1 + 10), (x1 + 10 - L, y1 + 10)], fill=rgba(GOLD, 0.9), width=3)
    d.line([(x1 + 10, y1 + 10), (x1 + 10, y1 + 10 - L)], fill=rgba(GOLD, 0.9), width=3)
    if firma: caps(d, (X0, y1 - 80), "Miguel Garcés", 24, MUTED, a, 0.34)
    if num: caps(d, (X1, y1 - 80), f"{num:02d} / {total:02d}", 24, MUTED, a, 0.3, anchor_right=True)

def scene_draw(c, sc, media, t, total_n):
    dur = sc["dur"]; a_out = clamp((dur - t) / 0.35) if not sc.get("ultima") else 1
    d = ImageDraw.Draw(c)
    y = 230
    if sc.get("seccion"):
        caps(d, (X0, y), sc["seccion"], 30, GOLD, ease(t / 0.6) * a_out)
        d.line([(X0, y + 64), (X0 + 70 * ease((t - 0.1) / 0.6), y + 64)], fill=rgba(GOLD, a_out), width=2)
        y += 130
    elif sc.get("filete"):
        d.line([(X0, y + 64), (X0 + 70 * ease((t - 0.1) / 0.6), y + 64)], fill=rgba(GOLD, a_out), width=2); y += 130
    for el in sc.get("orden", ["titulo", "ventana", "textos"]):
        if el == "titulo" and sc.get("titulo"):
            imgs = layout(sc["titulo"], 118, "Italic", CREAM, X1 - X0)
            y = place(c, imgs, 122, X0, y - 20, t, 0.2, stagger=0.25, alpha=a_out) + 40
        elif el == "ventana" and media:
            wh = sc.get("ventana", {}).get("alto", 440); ww = X1 - X0
            if sc.get("ventana", {}).get("ancho_total"): ww = FR[2] - FR[0] - 2; vx = FR[0] + 1
            else: vx = X0
            m = None
            for st, md in media:
                if t >= st: m, mt = md, t - st
            if m:
                im = m.frame(mt, ww, wh).convert("RGBA")
                k = ease(t / 0.6) * a_out
                im.putalpha(int(255 * k)); c.alpha_composite(im, (vx, int(y)))
                d = ImageDraw.Draw(c)
                d.rectangle([vx - 1, y - 1, vx + ww, y + wh], outline=rgba(GOLD, 0.35 * k), width=1)
            y += wh + 60
        elif el == "numero" and sc.get("numero"):
            f = sp(250, "Italic"); s = sc["numero"]
            im = Image.new("RGBA", (int(f.getlength(s)) + 30, 300), (0, 0, 0, 0)); ImageDraw.Draw(im).text((0, 0), s, font=f, fill=GOLD_L)
            y = place(c, [im], 0, X0 + 10, y - 40, t, 0.3, alpha=a_out, rise=40) + 300
            if sc.get("numero_pie"):
                caps(ImageDraw.Draw(c), (X0, y), sc["numero_pie"], 28, (200, 194, 180), ease((t - 0.8) / 0.6) * a_out, 0.36)
                y += 90
        elif el == "textos":
            for i, tx in enumerate(sc.get("textos", [])):
                size, style, col, lead = STYLES[tx.get("estilo", "cuerpo")]
                size = tx.get("tam", size); col = COLORS.get(tx.get("color"), col)
                imgs = layout(tx["texto"], size, style, col, X1 - X0)
                y = place(c, imgs, int(size * lead), X0, y, t, tx.get("desde", 0.4 + i * 1.0), alpha=a_out) + tx.get("espacio", 34)
        elif el == "firma" and sc.get("firma"):
            caps(ImageDraw.Draw(c), (X0, y), sc["firma"], 34, GOLD, ease((t - sc.get("firma_desde", 1.2)) / 0.8), 0.32); y += 80
        elif isinstance(el, int): y += el

def shade_bottom(c, y0, strength=0.92, top=False):
    """Fundido oscuro desde y0 hasta el borde (inferior, o superior si top)."""
    g = np.zeros((H, 1), np.float32)
    ys = np.arange(H, dtype=np.float32)
    if top: v = np.clip((y0 - ys) / 500, 0, 1)
    else: v = np.clip((ys - y0) / 500, 0, 1)
    g[:, 0] = (v ** 1.3) * strength * 255
    m = Image.fromarray(g.astype(np.uint8), "L").resize((W, H))
    dark = Image.new("RGBA", (W, H), BG + (255,)); dark.putalpha(m); c.alpha_composite(dark)

def full_draw(c, sc, media, t, chrome_layer):
    """Imagen a toda pantalla, textos fundidos encima."""
    dur = sc["dur"]; last = sc.get("ultima")
    m = None
    for st, md in media:
        if t >= st: m, mt = md, t - st
    k = ease(t / 0.45) * (1 if last else clamp((dur - t) / 0.35))
    if m:
        hh = int(m.s.get("alto", H))                         # "alto": ocupa solo la parte superior, a todo el ancho
        im = m.frame(mt, W, hh).convert("RGBA"); im.putalpha(int(255 * k))
        c.alpha_composite(im, (0, -int(m.s.get("sube", 0))))   # "sube": desplaza la imagen hacia arriba (px)
    top = sc.get("texto_arriba", False)
    if sc.get("textos") or sc.get("seccion") or sc.get("numero"):
        shade_bottom(c, sc.get("fundido", 820 if not top else 1050), sc.get("sombra", 0.94), top)
    c.alpha_composite(chrome_layer)
    a_out = 1 if last else clamp((dur - t) / 0.35)
    # componer el bloque de texto para alinearlo abajo (o arriba)
    items = []
    if sc.get("seccion"): items.append(("seccion", 100))
    if sc.get("numero"):
        items.append(("numero", 300))
        if sc.get("numero_pie"): items.append(("numero_pie", 80))
    for i, tx in enumerate(sc.get("textos", [])):
        size, style, col, lead = STYLES[tx.get("estilo", "cuerpo")]; size = tx.get("tam", size)
        col = COLORS.get(tx.get("color"), col)
        imgs = layout(tx["texto"], size, style, col, X1 - X0)
        items.append((("texto", imgs, int(size * lead), tx.get("desde", 0.5 + i * 1.0)), len(imgs) * int(size * lead) + tx.get("espacio", 30)))
    total_h = sum(h for _, h in items)
    y = 300 if top else sc.get("pie_y", 1480) - total_h
    d = ImageDraw.Draw(c)
    for it, h in items:
        if it == "seccion":
            caps(d, (X0, y), sc["seccion"], 30, GOLD, ease(t / 0.6) * a_out)
            d.line([(X0, y + 60), (X0 + 70 * ease((t - 0.1) / 0.6), y + 60)], fill=rgba(GOLD, a_out), width=2)
        elif it == "numero":
            f = sp(250, "Italic"); s_ = sc["numero"]
            im = Image.new("RGBA", (int(f.getlength(s_)) + 30, 300), (0, 0, 0, 0)); ImageDraw.Draw(im).text((0, 0), s_, font=f, fill=GOLD_L)
            place(c, [im], 0, X0 + 10, y - 50, t, 0.3, alpha=a_out, rise=40); d = ImageDraw.Draw(c)
        elif it == "numero_pie":
            caps(d, (X0, y), sc["numero_pie"], 28, CREAM, ease((t - 0.8) / 0.6) * a_out, 0.36)
        else:
            _, imgs, lh, st = it
            place(c, imgs, lh, X0, y, t, st, alpha=a_out); d = ImageDraw.Draw(c)
        y += h

def main(spec_path, preview=None):
    spec = json.load(open(spec_path)); base = os.path.dirname(os.path.abspath(spec_path))
    cache = os.path.join(base, ".cache_reel"); os.makedirs(cache, exist_ok=True)
    scenes = spec["escenas"]; scenes[-1]["ultima"] = True
    fmt = spec.get("formato", "ventana")          # "ventana" (imagen enmarcada) o "completo" (pantalla completa)
    numerar = spec.get("numerar", False)          # contador «01 / 07» al pie
    total_n = max([s.get("num", 0) for s in scenes] + [0])
    media = []
    for s in scenes:
        ms, st = [], 0.0
        for md in s.get("medios", []):
            st = md.get("en", st); ms.append((st, Medium(md, md.get("dur", s["dur"] - st), base, cache)))
        media.append(ms)
    total = sum(s["dur"] for s in scenes); n = int(total * FPS)
    rng = np.random.default_rng(3); G = [(rng.normal(0, 1, (H // 2, W // 2)) * 3.5).astype(np.float32) for _ in range(4)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = np.clip(1 - 0.25 * (((xx - W / 2) / (W * 0.8)) ** 2 + ((yy - H * 0.45) / (H * 0.7)) ** 2), 0.6, 1)[..., None]
    out = os.path.join(base, spec.get("salida", "reel.mp4"))
    if preview is None:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                               "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                               "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", out],
                              stdin=subprocess.PIPE)
    frames = range(n) if preview is None else [int(p * FPS) for p in preview]
    for fi in frames:
        tt = fi / FPS; acc = 0
        for idx, s in enumerate(scenes):
            if tt < acc + s["dur"] or idx == len(scenes) - 1: break
            acc += s["dur"]
        s, t = scenes[idx], tt - acc
        c = Image.new("RGBA", (W, H), BG + (255,))
        portada = s.get("portada", idx == 0)
        ventana = portada or s.get("formato", fmt) == "ventana"
        firma = bool(s.get("ultima"))          # «Miguel Garcés» solo al pie del último plano
        num = s.get("num") if numerar else None
        ch = Image.new("RGBA", (W, H), (0, 0, 0, 0)); chrome(ch, firma, num, total_n, 1.0, grid=s.get("reticula", False))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if ventana:
            c.alpha_composite(ch); scene_draw(layer, s, media[idx], t, total_n)
        else:
            full_draw(layer, s, media[idx], t, ch)
        if s.get("ultima"):
            k = clamp((total - tt) / 0.9); layer.putalpha(layer.getchannel("A").point(lambda v: int(v * k)))
        c.alpha_composite(layer)
        arr = np.asarray(c.convert("RGB")).astype(np.float32)
        g = np.repeat(np.repeat(G[fi % 4], 2, 0), 2, 1)[..., None]
        arr = np.clip(arr * vig + g, 0, 255).astype(np.uint8)
        if preview is None: ff.stdin.write(arr.tobytes())
        else: Image.fromarray(arr).save(os.path.join(base, f"prueba_{tt:05.1f}.png"))
    if preview is None:
        ff.stdin.close(); ff.wait(); print(f"Hecho: {out} ({total:.1f} s)")

if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    main(sys.argv[1], [float(x) for x in sys.argv[2:]] or None)
