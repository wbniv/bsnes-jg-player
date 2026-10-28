#!/usr/bin/env python3
"""Generate the TV library mockups for the library plan and the deferred search plan.

Writes docs/plans/2026-10-26-snes-rom-library-selector/ (library, no search) and
docs/plans/2026-10-26-snes-rom-library-search/ (search states).

Each mockup is a self-contained 1440x900 HTML page (inline CSS, base64 images) holding a
1920x1080 TV screen scaled to 0.75, plus a caption strip. Real titles, categories,
descriptions, controls lines and screenshots come from the sibling biohack.net checkout.
A same-basename PNG is captured with headless Chrome unless --no-png is given.
"""
import argparse
import base64
import html
import io
import json
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

from PIL import Image

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
LIBRARY_DIR = TOOLS.parent / "2026-10-26-snes-rom-library-selector"
SEARCH_DIR = TOOLS.parent / "2026-10-26-snes-rom-library-search"
SITE = ROOT.parent / "biohack.net"
COLLECTION = SITE / "src" / "content" / "snes"
PREVIEWS = SITE / "public" / "play" / "preview"
CATEGORY_LABELS = {
    "fractals": "Fractals", "physics": "Physics & Simulation", "cellular": "Cellular Automata",
    "motion": "Motion & Curves", "algorithms": "Algorithms & Data", "rendering": "Rendering & Graphics",
    "video": "Video Playback", "signals": "Signals & Audio", "bignums": "Big Numbers",
    "ciphers": "Ciphers & Bit Tricks", "classics": "Games & Classics", "cartridge": "Cartridge & Mapping Tests",
}
FAVORITES = {"space-invaders", "mandel-float", "mandel-display"}
ROW_PITCH = 112  # 100 px row + 12 px gap, in 1920x1080 TV pixels
E = html.escape

CSS = """
*{box-sizing:border-box}
body{margin:0;width:1440px;height:900px;overflow:hidden;background:#05080c;color:#eef4fb;
 font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans",sans-serif}
.frame{position:absolute;overflow:hidden;background:#000}
.tv{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0;overflow:hidden;
 background:linear-gradient(180deg,#121b28 0%,#0a0f17 100%)}
.cap{position:absolute;left:0;top:810px;width:1440px;height:90px;background:#0e1520;border-top:1px solid #2a3a4f;
 padding:12px 28px;font-size:15px;line-height:1.45;color:#c9d6e4}
.cap b{color:#fff}
.cap .tag{float:right;margin-left:16px;font:600 11px ui-monospace,monospace;letter-spacing:.06em;border:1px solid #3a4b61;
 border-radius:10px;padding:2px 8px;color:#9fb2c6}
.mini-label{position:absolute;font-size:15px;color:#c9d6e4}
.mini-label b{color:#fff}
.abs{position:absolute}
.title{left:96px;top:54px}
.title h1{margin:0;font-size:36px;line-height:44px;font-weight:700;letter-spacing:.01em}
.title p{margin:0;font-size:24px;line-height:30px;color:#a9b8c9}
.search{left:1204px;top:54px;width:620px;height:72px;border-radius:36px;background:#0b121c;border:2px solid #33465d;
 display:flex;align-items:center;gap:16px;padding:0 28px;font-size:28px;color:#8fa2b7}
.search .typed{color:#fff}
.search .caret{display:inline-block;width:3px;height:34px;background:#fff;vertical-align:middle;margin-left:2px}
.search.ime{border-color:#fff;box-shadow:0 0 0 4px #fff}
.lucky{left:836px;top:54px;height:72px;border-radius:36px;background:#1b2a3c;border:2px solid #33465d;display:flex;
 align-items:center;gap:14px;padding:0 32px;font-size:28px;font-weight:600}
.lucky.off{opacity:.35}
.chips{left:96px;top:150px;width:1728px;height:64px;display:flex;gap:16px;overflow:hidden;
 -webkit-mask-image:linear-gradient(90deg,#000 88%,transparent);mask-image:linear-gradient(90deg,#000 88%,transparent)}
.chip{flex:none;height:60px;border-radius:30px;padding:0 26px;display:flex;align-items:center;gap:10px;font-size:24px;
 font-weight:600;background:#172333;border:2px solid #2a3a4f;color:#c8d5e3}
.chip .n{font-weight:400;color:#8fa2b7}
.chip.sel{background:#d9e8f7;border-color:#d9e8f7;color:#0b1520}
.chip.sel .n{color:#41556b}
.focus{box-shadow:0 0 0 4px #fff,0 10px 30px #000c;transform:scale(1.03)}
.head{left:96px;top:226px;width:760px;display:flex;justify-content:space-between;font-size:24px;color:#a9b8c9}
.list{left:96px;top:262px;width:760px;height:698px;overflow:hidden;
 -webkit-mask-image:linear-gradient(180deg,#000 92%,transparent);mask-image:linear-gradient(180deg,#000 92%,transparent)}
.row{position:absolute;left:8px;width:740px;height:100px;border-radius:14px;background:#141e2b;border:1px solid #223247;
 display:flex;align-items:center;gap:22px;padding:0 22px 0 10px}
.row.focus{background:#24364d;border-color:#24364d}
.row.top{border:3px solid #7fb6e8}
.row img{width:96px;height:84px;border-radius:6px;flex:none;background:#000;object-fit:cover}
.row .txt{flex:1;min-width:0}
.row .t{font-size:30px;line-height:38px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .s{font-size:24px;line-height:30px;color:#a9b8c9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.star{color:#f2c35b}
.tags{display:flex;gap:10px;flex:none}
.tg{font-size:22px;font-weight:700;letter-spacing:.05em;padding:3px 12px;border-radius:8px;border:2px solid #4d6a88;color:#b9d3ec}
.tg.play{border-color:#58c08a;color:#8fe0b4}
.tg.topm{border-color:#7fb6e8;color:#cfe5fa}
.scroll{left:870px;top:262px;width:6px;height:698px;border-radius:3px;background:#1d2a3a}
.scroll i{position:absolute;left:0;width:6px;border-radius:3px;background:#8fa2b7}
.pv{left:892px;top:226px;width:932px;height:740px;display:grid;grid-template-columns:640px 268px;grid-template-rows:minmax(0,1fr);gap:24px;align-items:stretch}
.pv .shot{width:640px;height:560px;display:block;image-rendering:pixelated;border-radius:6px;background:#000}
.pv .details{grid-column:2;grid-row:1;min-width:0;min-height:0;max-height:100%;overflow-y:auto;display:flex;flex-direction:column}
.pv h2{margin:0;font-size:34px;line-height:42px;font-weight:700}
.pv .meta{margin-top:10px;font-size:23px;line-height:30px;color:#a9b8c9}
.pv .desc{margin-top:18px;font-size:24px;line-height:34px;color:#d5e0ec;overflow-wrap:anywhere}
.pv .ctl{margin-top:10px;font-size:24px;line-height:32px;color:#a9b8c9;white-space:normal;overflow-wrap:anywhere}
.pv .file{margin-top:6px;font:22px/30px ui-monospace,"DejaVu Sans Mono",monospace;color:#8fa2b7}
.pv .actions{display:flex;flex-direction:column;gap:10px;margin-top:auto;padding-top:14px}
.pv .actions .fav,.pv .actions .play{height:48px;border-radius:24px;padding:0 16px;display:flex;align-items:center;justify-content:center;gap:10px;
 font-size:23px;font-weight:600;background:#172333;border:2px solid #2a3a4f;color:#eef4fb}
.pv .actions .fav{border-color:#9e824c;color:#ffdc8e}
.pv .actions .play{border-color:#4d95bc;background:#17374d;color:#eef4fb}
.err{margin-top:14px;border:3px solid #e07a6a;background:#2a1513;border-radius:12px;padding:16px 20px;font-size:24px;line-height:34px}
.err b{color:#ffb4a8}
.hints{left:96px;top:996px;width:1728px;display:flex;gap:40px;font-size:24px;color:#a9b8c9;align-items:center}
.k{display:inline-block;font:700 20px/1 ui-monospace,"DejaVu Sans Mono",monospace;letter-spacing:.05em;color:#0b1520;
 background:#c8d5e3;border-radius:8px;padding:6px 10px;margin-right:10px}
.empty{left:96px;top:262px;width:1728px;height:660px;display:flex;flex-direction:column;align-items:center;justify-content:center;
 text-align:center;gap:18px}
.empty .big{font-size:120px;line-height:1;color:#4d6a88}
.empty h2{margin:0;font-size:40px}
.empty p{margin:0;font-size:28px;color:#a9b8c9;max-width:1100px;line-height:40px}
.btn{height:72px;border-radius:36px;padding:0 34px;display:inline-flex;align-items:center;font-size:28px;font-weight:600;
 background:#1b2a3c;border:2px solid #33465d}
.kbd{left:0;top:620px;width:1920px;height:460px;background:#202124;border-top:2px solid #3c4043;padding:28px 220px}
.kbd .sug{height:56px;display:flex;gap:18px;margin-bottom:22px}
.kbd .sug span{font-size:26px;color:#e8eaed;padding:8px 22px;border-radius:28px;background:#303134}
.kbd .r{display:flex;gap:14px;margin-bottom:14px;justify-content:center}
.kbd .r span{width:96px;height:72px;border-radius:12px;background:#3c4043;color:#e8eaed;font-size:30px;display:flex;
 align-items:center;justify-content:center}
.kbd .r span.w{width:260px}.kbd .r span.ww{width:520px}
.kbd .r span.f{background:#e8eaed;color:#202124;box-shadow:0 0 0 4px #8ab4f8}
.kbd .lbl{position:absolute;right:40px;top:20px;font:600 18px ui-monospace,monospace;color:#9aa0a6;letter-spacing:.06em}
.game{left:343px;top:0;width:1234px;height:1080px;image-rendering:pixelated;display:block}
.dim{left:0;top:0;width:1920px;height:1080px;background:#000a}
.card{left:580px;top:150px;width:760px;border-radius:24px;background:linear-gradient(160deg,#182637,#0f1822);border:2px solid #30445c;
 padding:36px;box-shadow:0 20px 60px #000c}
.card .hd{display:flex;gap:24px;align-items:center;margin-bottom:28px}
.card .hd img{width:128px;height:112px;image-rendering:pixelated;border-radius:8px}
.card .hd small{font-size:24px;color:#a9b8c9;display:block}
.card .hd strong{font-size:36px;line-height:44px;display:block}
.card .act{height:76px;border-radius:14px;background:#172333;border:2px solid #2a3a4f;margin-top:14px;display:flex;
 align-items:center;padding:0 28px;font-size:28px;font-weight:600}
.card .act.focus{background:#2c4561;border-color:#2c4561}
.card .act .sub{margin-left:auto;font-size:22px;font-weight:400;color:#a9b8c9}
.card hr{border:0;border-top:1px solid #30445c;margin:22px 0 8px}
.load{left:430px;top:820px;width:1060px;border-radius:20px;background:#0d1520ee;border:2px solid #30445c;padding:28px 36px}
.load h2{margin:0;font-size:36px}
.load p{margin:6px 0 18px;font-size:24px;color:#a9b8c9}
.bar{height:12px;border-radius:6px;background:#22324a}
.bar i{display:block;height:12px;border-radius:6px;background:#7fb6e8}
"""

ICON_SEARCH = ('<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">'
               '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21"/></svg>')
ICON_DIE = ('<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
            '<rect x="3" y="3" width="18" height="18" rx="4"/><circle cx="8" cy="8" r="1.4" fill="currentColor"/>'
            '<circle cx="16" cy="16" r="1.4" fill="currentColor"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/>'
            '<circle cx="16" cy="8" r="1.4" fill="currentColor"/><circle cx="8" cy="16" r="1.4" fill="currentColor"/></svg>')


def load_catalog():
    roms = []
    for path in COLLECTION.glob("*.json"):
        d = json.loads(path.read_text(encoding="utf-8"))
        keys = d["keys"].strip()
        roms.append({
            "slug": d["slug"], "title": d["title"], "category": CATEGORY_LABELS.get(d["category"], d["category"]),
            "desc": d["desc"], "keys": keys, "order": d["order"], "mode7": d.get("displayMode") == 7,
            "interactive": not re.match(r"(self-running|no controls)", keys, re.I),
            "size": (SITE / "public" / "play" / "roms" / f"{d['slug']}.sfc").stat().st_size
            if (SITE / "public" / "play" / "roms" / f"{d['slug']}.sfc").exists() else 32768,
        })
    roms.sort(key=lambda r: (-r["order"], r["slug"]))
    return roms


_IMG = {}


def img(slug):
    if slug not in _IMG:
        im = Image.open(PREVIEWS / f"{slug}.png").convert("RGB").quantize(256)
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        _IMG[slug] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return _IMG[slug]


def fold(text):
    text = unicodedata.normalize("NFKD", text.replace("π", " pi "))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.findall(r"[a-z0-9]+", text)


def search(roms, query):
    terms = fold(query)
    hits = []
    for r in roms:
        title = fold(r["title"])
        words = title + fold(r["slug"]) + fold(r["category"]) + (["mode", "7"] if r["mode7"] else []) + \
            (["interactive"] if r["interactive"] else [])
        if not all(any(w.startswith(t) for w in words) for t in terms):
            continue
        score = 3 if " ".join(title).startswith(" ".join(terms)) else \
            2 if all(any(w.startswith(t) for w in title) for t in terms) else 1
        hits.append((score, r))
    hits.sort(key=lambda h: (-h[0], -h[1]["order"]))
    return [r for _, r in hits]


def size_label(n):
    return f"{n // 1048576}&nbsp;MB" if n >= 1048576 else f"{n // 1024}&nbsp;KB"


def tags(r, paused=None, top=False):
    out = []
    if top:
        out.append('<span class="tg topm">TOP MATCH</span>')
    if paused == r["slug"]:
        out.append('<span class="tg play">▶ PAUSED</span>')
    if r["interactive"]:
        out.append('<span class="tg">INTERACTIVE</span>')
    if r["mode7"]:
        out.append('<span class="tg">MODE 7</span>')
    return '<div class="tags">' + "".join(out) + "</div>"


def row(r, y, focus=False, sub=None, paused=None, top=False, cls=""):
    star = ' <span class="star">★</span>' if r["slug"] in FAVORITES else ""
    sub = r["category"] if sub is None else sub
    c = "row" + (" focus" if focus else "") + (" top" if top else "") + (" " + cls if cls else "")
    return (f'<div class="{c}" style="top:{y}px"><img src="{img(r["slug"])}" alt="">'
            f'<div class="txt"><div class="t">{E(r["title"])}{star}</div><div class="s">{E(sub)}</div></div>'
            f'{tags(r, paused, top)}</div>')


def topbar(total, query=None, ime=False, lucky=True, sub=None, search=False):
    field = (f'<span class="typed">{E(query)}</span><span class="caret"></span>' if ime else
             f'<span class="typed">{E(query)}</span>' if query else f"Search {total} ROMs")
    return (f'<div class="abs title"><h1>LLVM 65816 Torture Test Suite</h1>'
            f'<p>{E(sub or f"{total} ROMs on SNES · plays offline")}</p></div>'
            f'<div class="abs lucky{"" if lucky else " off"}"{"" if search else " style=\"left:auto;right:96px\""}>'
            f'{ICON_DIE}<span>I\'m Feeling Lucky</span></div>'
            + (f'<div class="abs search{" ime" if ime else ""}">{ICON_SEARCH}<span>{field}</span></div>' if search else ""))


def chips(roms, selected="All", focused=None, fav_count=None, counts=None):
    counts = counts or {}
    if not counts:
        for r in roms:
            counts[r["category"]] = counts.get(r["category"], 0) + 1
    fav = len([r for r in roms if r["slug"] in FAVORITES]) if fav_count is None else fav_count
    items = [("All", len(roms)), ("★ Favorites", fav)] + sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    out, x, shift = [], 0, 0
    for name, n in items:
        w = 60 + 14 * len(name) + 14 * len(f"{n:,}") + 16
        if name == selected and x + w > 1400:
            shift = x + w - 1400
        x += w
    for name, n in items:
        c = "chip" + (" sel" if name == selected else "") + (" focus" if name == focused else "")
        out.append(f'<div class="{c}">{E(name)} <span class="n">{n:,}</span></div>')
    pad = f'<div style="flex:none;width:0;margin-left:-{shift}px"></div>' if shift else ""
    return '<div class="abs chips">' + pad + "".join(out) + "</div>"


def preview(r, error=None, fav_focus=False):
    fav = r["slug"] in FAVORITES
    meta = E(r["category"]) + (" · Mode 7" if r["mode7"] else "")
    favbtn = (f'<span class="fav{" focus" if fav_focus else ""}"><span class="star">{"★" if fav else "☆"}</span>'
              f'{"Favorite" if fav else "Add to Favorites"}</span>')
    if error:
        body = f'<div class="err"><b>Couldn\'t start this ROM.</b><br>{error}</div>'
    else:
        ctl = ("Controls: " + r["keys"]) if r["interactive"] else r["keys"].split(" — ")[0].split(" - ")[0]
        body = (f'<div class="desc">{E(r["desc"])}</div><div class="ctl">{E(ctl)}</div>'
                f'<div class="file">{E(r["slug"])}.sfc · {size_label(r["size"])}</div>')
    return (f'<div class="abs pv"><img class="shot" src="{img(r["slug"])}" alt="">'
            f'<div class="details"><h2>{E(r["title"])}</h2><div class="meta">{meta}</div>{body}'
            f'<div class="actions">{favbtn}<span class="play">▶ Play</span></div></div></div>')


def hints(items, style=""):
    return f'<div class="abs hints" style="{style}">' + "".join(f'<span><span class="k">{k}</span>{E(v)}</span>' for k, v in items) + "</div>"


def scrollbar(index, total, visible=6):
    h = max(40, round(698 * visible / max(total, visible)))
    y = round((698 - h) * index / max(total - 1, 1))
    return f'<div class="abs scroll"><i style="top:{y}px;height:{h}px"></i></div>'


def list_view(roms, focus_slug, band=2, paused=None, sub=None):
    i = focus_slug if isinstance(focus_slug, int) else next(k for k, r in enumerate(roms) if r["slug"] == focus_slug)
    start = max(0, min(i - band, len(roms) - 6))
    rows = "".join(row(r, (k - start) * ROW_PITCH, focus=(k == i), paused=paused,
                       sub=(sub(r) if sub else None))
                   for k, r in enumerate(roms[start:start + 7], start))
    return i, f'<div class="abs list">{rows}</div>'


def tv(inner, scale=0.75, left=0, top=0, width=1440, height=810):
    return (f'<div class="frame" style="left:{left}px;top:{top}px;width:{width}px;height:{height}px">'
            f'<div class="tv" style="transform:scale({scale})">{inner}</div></div>')


def page(title, body, caption, tag="MOCKUP — NOT SHIPPED"):
    cap = f'<div class="cap"><span class="tag">{tag}</span>{caption}</div>' if caption else ""
    return (f'<!DOCTYPE html>\n<!-- Generated by docs/plans/tools/generate-tv-library-mockups.py; edit the generator, not this file. -->\n'
            f'<html lang="en"><head><meta charset="utf-8"><title>Mockup — {E(title)}</title>'
            f'<style>{CSS}</style></head><body>{body}{cap}</body></html>\n')


def browse_screen(roms, focus_slug, paused=None, fav_focus=False, error=None, back="Back to top", head_left=None,
                  search=False):
    i, lst = list_view(roms, focus_slug, paused=paused)
    r = roms[i]
    return (topbar(len(roms), search=search) + chips(roms) +
            f'<div class="abs head"><span>{head_left or "All ROMs · newest first"}</span><span>{i + 1} of {len(roms):,}</span></div>'
            + lst + scrollbar(i, len(roms)) + preview(r, error=error, fav_focus=fav_focus) +
            hints([("D-PAD", "Browse"), ("SELECT", "Play" if not error else "Try again"),
                   ("HOLD SELECT", "Favorite"), ("BACK", back)]))


def build(roms):
    by = {r["slug"]: r for r in roms}
    lib, srch = {}, {}

    lib["01-browse"] = page("Browse", tv(browse_screen(roms, "mandel-float")),
        "<b>Browse — loaded, 152 ROMs.</b> Relaunch restores focus to the last-played ROM (Soft-Float Mandelbrot). One "
        "single-column list; focus stays in the third row while the list scrolls under it. The preview carries what a "
        "viewer needs: a 2.5× pixel-exact screenshot in a wide image stage, with metadata in a compact side rail. Gold means Favorites "
        "and nothing else. Card art is each ROM’s image from the biohack.net gallery. No search in this release.")

    hits = search(roms, "mand")
    rows = "".join(row(r, k * ROW_PITCH, top=(k == 0)) for k, r in enumerate(hits[:4]))
    kb_rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    kbd = ('<div class="abs kbd"><div class="lbl">SYSTEM KEYBOARD</div>'
           '<div class="sug"><span>mandel</span><span>mandelbrot</span><span>man</span></div>'
           + "".join('<div class="r">' + "".join(f'<span{" class=\"f\"" if ch == "d" else ""}>{ch}</span>' for ch in kr)
                     + "</div>" for kr in kb_rows)
           + '<div class="r"><span class="w">⌫</span><span class="ww">space</span><span class="w">Search ⏎</span></div></div>')
    srch["01-search-keyboard"] = page("Search with keyboard open", tv(
        topbar(len(roms), "mand", ime=True, search=True) +
        f'<div class="abs head" style="top:150px"><span>{len(hits)} matches for “mand”</span><span>Search ⏎ jumps to the top match</span></div>'
        f'<div class="abs list" style="top:196px;height:430px;-webkit-mask-image:none;mask-image:none">{rows}</div>' + kbd),
        "<b>Search — keyboard open.</b> Matching is word-prefix and accent/punctuation-blind across title, slug, "
        "category and tags, so “mand” finds all four Mandelbrots even though no title starts with it. The top match is "
        "marked instead of ghost text the remote can’t accept; the keyboard’s Search key closes it and focuses that row. "
        "Assumes Google TV shows a bottom-panel keyboard for WebView inputs — verify on cast1.")

    lib["02-favorites-empty"] = page("Favorites empty", tv(
        topbar(len(roms), lucky=False) + chips(roms, selected="★ Favorites", focused="★ Favorites", fav_count=0) +
        '<div class="abs empty"><div class="big">☆</div><h2>No favorites yet</h2>'
        '<p>Hold <span class="k">SELECT</span> on any ROM, or choose <b>☆ Add to Favorites</b> in its preview, '
        'and it will be kept here — on this TV, across restarts.</p></div>' +
        hints([("D-PAD ◀ ▶", "Change filter"), ("BACK", "Exit")])),
        "<b>Favorites — empty.</b> First-run state of the Favorites filter. A chip applies once focus rests on it, so focus "
        "stays on the chip (there is nothing below it to focus). I’m Feeling Lucky dims and is skipped by focus while the result set is empty. The message "
        "teaches the two ways to add a favorite instead of just saying “nothing here”.")

    cat_counts = {}
    for r in roms:
        cat_counts[r["category"]] = cat_counts.get(r["category"], 0) + 1
    global_hits = search(roms, "invaders")
    srch["02-no-matches"] = page("No matches", tv(
        topbar(len(roms), "invaders", lucky=False, search=True) + chips(roms, selected="Fractals") +
        '<div class="abs empty"><div class="big">⌕</div><h2>No Fractals match “invaders”</h2>'
        f'<p>{len(global_hits)} match in all ROMs.</p>'
        f'<div style="display:flex;gap:24px;margin-top:12px"><span class="btn focus">Search all {len(roms)} ROMs</span>'
        '<span class="btn">Clear search</span></div></div>' +
        hints([("SELECT", "Search all ROMs"), ("BACK", "Exit")])),
        "<b>Search + category — no matches.</b> Search applies inside the active filter (so Lucky can draw from it), "
        "but an empty result is never a dead end: the escape hatch already knows the global count, and it takes focus.")

    apollo = by["apollo-daylight"]
    lib["03-loading"] = page("Loading a large ROM", tv(
        f'<img class="abs game" src="{img("apollo-daylight")}" alt="" style="opacity:.35">'
        f'<div class="abs load"><h2>{E(apollo["title"])}</h2><p>Loading {size_label(apollo["size"])} ROM · Video Playback · Mode 7</p>'
        '<div class="bar"><i style="width:62%"></i></div></div>' +
        hints([("BACK", "Cancel and return to the library")], style="top:54px")),
        "<b>Loading — 4&nbsp;MB ROM.</b> Shown the moment Select is pressed (and after I’m Feeling Lucky, so the viewer "
        "sees what was drawn). The screenshot fills the game area dimmed; further Select presses are ignored; Back "
        "cancels. Large Video and Cartridge ROMs (4–8&nbsp;MB) are the ones that make this visible on a Chromecast.")

    lib["04-load-error"] = page("Load failed", tv(browse_screen(
        roms, "svx2-fastrom-video", paused="mandel-float",
        error="<code>svx2-fastrom-video.sfc</code> · 8&nbsp;MB · out of memory<br>"
              '<span class="k">SELECT</span>Try again &nbsp; <span class="k">BACK</span>Resume previous ROM',
        back="Resume Soft-Float Mandelbrot")),
        "<b>Load failed.</b> The library stays open with focus on the ROM that failed; the error replaces its "
        "description in the preview, title first, filename second, plain-language reason. The game that was paused "
        "(Soft-Float Mandelbrot) stays paused — it does not start running behind the library — and Back resumes it.")

    md = by["mandel-display"]
    # mandel-display's published preview is its 4x4 first pass; mandel-oop renders the same image.
    pause = (f'<img class="abs game" src="{img("mandel-oop")}" alt=""><div class="abs dim"></div>'
             f'<div class="abs card"><div class="hd"><img src="{img("mandel-oop")}" alt=""><div><small>Paused</small>'
             f'<strong>{E(md["title"])}</strong><small>Fractals · Mode 7</small></div></div>'
             '<div class="act focus">Resume</div><div class="act">Choose another ROM<span class="sub">152 in library</span></div>'
             '<div class="act">Restart this ROM</div><div class="act">Verify from start<span class="sub">self-check</span></div>'
             '<hr><div class="act">Exit to Google TV</div></div>')
    lib["05-pause-menu"] = page("Pause menu", tv(pause),
        "<b>Pause menu.</b> One vertical list (D-pad up/down only), ordered by likelihood: Resume, then Choose another ROM. "
        "The header names the paused ROM so “Restart” is unambiguous. Verify appears only for ROMs with a self-check; "
        "Exit is separated so it can’t be hit by overshooting.")

    synthetic = [dict(r, slug=r["slug"], title=f'{r["title"]}' if k < len(roms) else f'{r["title"]} #{k // len(roms) + 1}')
                 for k, r in enumerate(roms * 7)][:1000]
    ten = [by[s] for s in ["mandel-float", "burning-ship", "space-invaders", "doom-fire", "apollo-daylight", "rdiff",
                           "avalanche", "tea", "spigot", "life"]]
    sc = 704 / 1920
    one = (f'<img class="abs game" src="{img("mandel-oop")}" alt="">'
           + hints([("BACK", "Pause")], style="top:54px"))

    def small_list(cat, focus, title_sub, show_search, show_chips):
        i, lst = list_view(cat, focus)
        bar = topbar(len(cat), sub=title_sub, search=show_search)
        return (bar + (chips(cat) if show_chips else "") +
                f'<div class="abs head"><span>All ROMs</span><span>{i + 1} of {len(cat):,}</span></div>'
                + lst + scrollbar(i, len(cat)) + preview(cat[i]) +
                hints([("D-PAD", "Browse"), ("SELECT", "Play"), ("BACK", "Exit")]))

    ten_screen = (f'<div class="abs title"><h1>LLVM 65816 Torture Test Suite</h1><p>10 ROMs on SNES · plays offline</p></div>'
                  f'<div class="abs lucky" style="left:1404px">{ICON_DIE}<span>I\'m Feeling Lucky</span></div>'
                  + list_view(ten, "burning-ship")[1].replace("top:262px", "top:180px") + scrollbar(1, 10) + preview(by["burning-ship"]) +
                  hints([("D-PAD", "Browse"), ("SELECT", "Play"), ("BACK", "Exit")]))
    hundred = roms[:100]
    frames = [
        (one, "<b>1 ROM</b> — no library; boots straight in. Pause menu hides “Choose another ROM”."),
        (ten_screen, "<b>10 ROMs</b> — list + preview + Lucky. No filters: everything fits in two screens."),
        (small_list(hundred, hundred[40]["slug"], "100 ROMs on SNES · plays offline", False, True),
         "<b>100 ROMs</b> — full layout: filters with counts, list, preview."),
        (small_list(synthetic, 612, "1,000 ROMs on SNES · synthetic test catalog", False, True),
         "<b>1,000 ROMs</b> — same layout; list virtualized (≈20 rows in the DOM). At this size, un-defer search."),
    ]
    body = ""
    for k, (inner, label) in enumerate(frames):
        x, y = 16 + (k % 2) * 712, 14 + (k // 2) * 444
        body += tv(inner, scale=sc, left=x, top=y, width=704, height=396)
        body += f'<div class="mini-label" style="left:{x}px;top:{y + 402}px;width:704px">{label}</div>'
    lib["06-catalog-scale"] = page("Catalog scale 1 / 10 / 100 / 1,000", body, None)

    srch["03-browse-with-search"] = page("Browse with search", tv(browse_screen(roms, "mandel-float", search=True)),
        "<b>Where search would sit.</b> The field joins the top bar beside I’m Feeling Lucky, only when the catalog has more "
        "than 24 ROMs. Focusing it does nothing; Select opens the keyboard, so browsing never raises it by accident.")
    return {LIBRARY_DIR: lib, SEARCH_DIR: srch}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-png", action="store_true", help="write the HTML files only")
    args = parser.parse_args()
    if not COLLECTION.is_dir() or not PREVIEWS.is_dir():
        raise SystemExit(f"Expected the biohack.net checkout at {SITE}")
    roms = load_catalog()
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    for name, text, folder in [(n, t, d) for d, pages in build(roms).items() for n, t in pages.items()]:
        folder.mkdir(exist_ok=True)
        out = folder / f"{name}.html"
        out.write_text(text, encoding="utf-8")
        size = out.stat().st_size
        if size > 512 * 1024:
            raise SystemExit(f"{out.name} is {size:,} bytes; the bundle limit is 512 KB per file")
        if args.no_png or not chrome:
            continue
        png = folder / f"{name}.png"
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                        "--window-size=1440,900", f"--screenshot={png}", out.as_uri()],
                       check=True, capture_output=True)
        if png.stat().st_size > 480 * 1024:
            Image.open(png).convert("RGB").quantize(256).save(png, optimize=True)
        print(f"{folder.name}/{name}: {size:,} B html, {png.stat().st_size:,} B png")


if __name__ == "__main__":
    main()
