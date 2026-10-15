#!/usr/bin/env python3
"""
Nitrato — genera todo el sitio a partir de las bobinas guardadas en bobinas_json/.

Uso:
    python3 generate.py

Cada bobina es un JSON en bobinas_json/AAAA-MM-DD.json con esta forma:

{
  "number": 1,                       # n.º de bobina (1, 2, 3...)
  "date": "2026-10-13",
  "date_long": "13 de octubre de 2026",
  "section": "proceso",              # proceso | archivo | error | version
  "slug": "titulo-corto",
  "title": "Titular",
  "dek": "Una frase de bajada.",
  "ficha": [                         # ficha técnica de la obra (o de las obras)
    {"label": "Obra", "value": "El espíritu de la colmena"},
    {"label": "Año", "value": "1973"}
  ],
  "paragraphs": ["Párrafo...", "***", "Párrafo tras un corte de escena..."],
  "sources": [{"title": "Título de la fuente", "url": "https://..."}]
}

El script reconstruye cada vez index.html, archivo.html y piezas/*.html a partir
de todos los JSON, de modo que corregir una bobina antigua es tan sencillo como
editar su JSON y volver a ejecutarlo.
"""
import html
import json
import re
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "https://nitrato-garces.github.io/nitrato"
AUTHOR = "Miguel Garcés"

SECTIONS = {
    "proceso": ("El proceso", "Cómo se hizo algo concreto, contado desde dentro del oficio."),
    "archivo": ("El archivo vivo", "Una obra de hace décadas y las condiciones que la hicieron posible."),
    "error": ("El error", "Rodajes que descarrilaron, presupuestos que estallaron, obras que se perdieron."),
    "version": ("La versión que no viste", "Montajes alternativos, finales cortados, copias distintas de la misma película."),
}
ROTATION = ["proceso", "archivo", "error", "version"]

FONTS = ("https://fonts.googleapis.com/css2?"
         "family=Big+Shoulders+Display:wght@700;800"
         "&family=Big+Shoulders+Stencil+Display:wght@900"
         "&family=Big+Shoulders+Text:wght@600;700"
         "&family=Spectral:ital,wght@0,400;0,600;1,400&display=swap")


def esc(s):
    return html.escape(str(s), quote=True)


def words(reel):
    return sum(len(p.split()) for p in reel["paragraphs"])


def minutes(reel):
    return max(1, round(words(reel) / 220))


def section_name(reel):
    return SECTIONS[reel["section"]][0]


def page(*, title, description, rel, canonical, body, edge, og_type="website", current=""):
    nav = []
    for href, label in (("index.html", "Última bobina"), ("archivo.html", "Archivo")):
        cur = ' aria-current="page"' if current == href else ""
        nav.append(f'<a href="{rel}{href}"{cur}>{label}</a>')
    edge_text = esc(("   " + edge + "   ") * 40)
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="author" content="{AUTHOR}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Nitrato">
<link rel="canonical" href="{canonical}">
<meta name="twitter:card" content="summary">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%231d1310'/%3E%3Crect x='4' y='4' width='6' height='6' fill='%23eaa23a'/%3E%3Crect x='4' y='13' width='6' height='6' fill='%23eaa23a'/%3E%3Crect x='4' y='22' width='6' height='6' fill='%23eaa23a'/%3E%3Crect x='14' y='4' width='14' height='24' fill='%23eaa23a'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{rel}assets/style.css">
</head>
<body>
<div class="filmedge" aria-hidden="true"><span>{edge_text}</span></div>
<div class="page">
<header class="masthead">
  <a class="brand" href="{rel}index.html">
    <span class="brand-word">NITRATO</span>
    <span class="brand-line">Lo que una película fue antes de ser la película. Por {AUTHOR}.</span>
  </a>
  <nav class="mast-nav">{''.join(nav)}</nav>
</header>
<main>
{body}
</main>
<footer>Nitrato, de {AUTHOR}. Una bobina nueva cada dos días.</footer>
</div>
<script src="{rel}assets/script.js"></script>
</body>
</html>
"""


def reel_meta(reel):
    return (f'<p class="reel-meta"><span>Bobina {reel["number"]}</span>'
            f'<span class="section-name">{esc(section_name(reel))}</span>'
            f'<span>{esc(reel["date_long"])}</span>'
            f'<span>{minutes(reel)} min de lectura</span></p>')


def ficha(reel):
    if not reel.get("ficha"):
        return ""
    cells = "".join(f'<div><dt>{esc(f["label"])}</dt><dd>{esc(f["value"])}</dd></div>' for f in reel["ficha"])
    return f'<dl class="ficha">{cells}</dl>'


def paragraphs(items):
    out = []
    for p in items:
        if p.strip() in ("***", "* * *"):
            out.append('<p class="scene-break" aria-hidden="true">· · ·</p>')
        else:
            out.append(f"<p>{esc(p)}</p>")
    return "\n".join(out)


def piece_path(reel):
    return f"piezas/{reel['date']}-{reel['slug']}.html"


def render_piece(reel):
    url = f"{BASE}/{piece_path(reel)}"
    share_text = urllib.parse.quote(f"{reel['title']} — Nitrato")
    share_url = urllib.parse.quote(url, safe="")
    sources = ""
    if reel.get("sources"):
        items = "".join(f'<li><a href="{esc(s["url"])}" rel="noopener">{esc(s["title"])}</a></li>' for s in reel["sources"])
        sources = f'<section class="sources"><h2>Fuentes consultadas</h2><ol>{items}</ol></section>'
    body = f"""<article>
  <div class="lead">
    {reel_meta(reel)}
    <h1>{esc(reel['title'])}</h1>
    <p class="dek">{esc(reel['dek'])}</p>
    <p class="byline">Por <strong>{AUTHOR}</strong></p>
  </div>
  {ficha(reel)}
  <div class="body">
{paragraphs(reel['paragraphs'])}
  </div>
  {sources}
  <div class="share">
    <a class="share-btn" target="_blank" rel="noopener" href="https://twitter.com/intent/tweet?text={share_text}&url={share_url}">Compartir en X</a>
    <a class="share-btn" target="_blank" rel="noopener" href="https://wa.me/?text={share_text}%20{share_url}">WhatsApp</a>
    <button class="share-btn" type="button" data-copy="{url}"><span class="copy-label">Copiar enlace</span></button>
  </div>
</article>"""
    return page(title=f"{reel['title']} — Nitrato", description=reel["dek"], rel="../",
                canonical=url, body=body, og_type="article",
                edge=f"NITRATO   BOBINA {reel['number']:03d}   {section_name(reel).upper()}")


def reel_list(reels, rel=""):
    if not reels:
        return '<p class="empty">Todavía no hay bobinas anteriores.</p>'
    items = []
    for r in reels:
        items.append(
            f'<li><span class="reel-num">{r["number"]}</span><div>'
            f'<a href="{rel}{piece_path(r)}">{esc(r["title"])}</a>'
            f'<span class="meta"><span class="section-name">{esc(section_name(r))}</span>, {esc(r["date_long"])}</span>'
            f'</div></li>')
    return '<ol class="reel-list">' + "".join(items) + "</ol>"


def lede(reel, n=2):
    paras = [p for p in reel["paragraphs"] if p.strip() not in ("***", "* * *")][:n]
    return paragraphs(paras)


def render_index(reels):
    if not reels:
        body = '<div class="lead"><h2>La primera bobina está en el proyector.</h2></div>'
    else:
        last, rest = reels[0], reels[1:]
        href = piece_path(last)
        body = f"""<div class="lead">
  {reel_meta(last)}
  <h2><a href="{href}">{esc(last['title'])}</a></h2>
  <p class="dek">{esc(last['dek'])}</p>
  <p class="byline">Por <strong>{AUTHOR}</strong></p>
</div>
{ficha(last)}
<div class="body">
{lede(last)}
<a class="continue" href="{href}">Seguir leyendo</a>
</div>
<section class="reels">
  <h2>Bobinas anteriores</h2>
  {reel_list(rest)}
</section>"""
    return page(title="Nitrato", description="Lo que una película fue antes de ser la película. Por Miguel Garcés.",
                rel="", canonical=f"{BASE}/", body=body, current="index.html",
                edge="NITRATO   INFLAMABLE   FRÁGIL   HISTÓRICO")


def render_archive(reels):
    secs = "".join(f"<dt>{esc(n)}</dt><dd>{esc(d)}</dd>" for n, d in SECTIONS.values())
    body = f"""<div class="lead">
  <h1>Archivo</h1>
  <p class="dek">Todas las bobinas, de la más reciente a la primera.</p>
</div>
<dl class="secciones">{secs}</dl>
<section class="reels">
  {reel_list(reels)}
</section>"""
    return page(title="Archivo — Nitrato", description="Todas las bobinas de Nitrato.", rel="",
                canonical=f"{BASE}/archivo.html", body=body, current="archivo.html",
                edge="NITRATO   ARCHIVO")


def load():
    reels = []
    for f in sorted((ROOT / "bobinas_json").glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        assert r["section"] in SECTIONS, f"{f.name}: sección desconocida {r['section']}"
        assert re.fullmatch(r"[a-z0-9-]+", r["slug"]), f"{f.name}: slug no válido"
        reels.append(r)
    reels.sort(key=lambda r: r["number"], reverse=True)
    return reels


def main():
    reels = load()
    (ROOT / "piezas").mkdir(exist_ok=True)
    for r in reels:
        (ROOT / piece_path(r)).write_text(render_piece(r), encoding="utf-8")
        print("  pieza:", piece_path(r), f"({words(r)} palabras)")
    (ROOT / "index.html").write_text(render_index(reels), encoding="utf-8")
    (ROOT / "archivo.html").write_text(render_archive(reels), encoding="utf-8")
    nxt = len(reels) + 1
    print(f"  portada y archivo actualizados. Próxima bobina: n.º {nxt}, sección «{SECTIONS[ROTATION[(nxt - 1) % 4]][0]}»")


if __name__ == "__main__":
    main()
