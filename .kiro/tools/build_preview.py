#!/usr/bin/env python3
"""يبني صفحاتَ معاينةٍ معزولةٍ من index.html — **بمصدرٍ واحدٍ لا نسخةٍ ثانية**.

الرسومُ المتجهيّةُ تُقتَطع من index.html عند كلِّ تشغيل، فلا تتباعد نسخةُ
المعاينةِ عن الأصلِ بصمت.

وقيدٌ مقيسٌ في هذا الصندوق: **صفرُ خطوطٍ عربيّة** (`fc-list` = 10 خطوط،
صفر عربي). فاللقطةُ العربيّةُ تُظهر مربّعاتٍ فارغة، ومنه قاعدتان:
  · لا تُرسَل لقطةٌ عربيّةٌ للعميل، ولا يُحكَم بها على قراءةِ النصّ
  · للحكمِ على التبايُنِ والتخطيطِ: صفحةُ اختبارٍ بنصٍّ **لاتيني**
  · واللقطةُ صحيحةٌ ومفيدةٌ للمكوّناتِ البصريّةِ **الخاليةِ من النصّ**

ويُعطَّل `[data-reveal]` في المعاينة لأنّه يبدأ `opacity:0` ولا يُظهره
إلّا الجافاسكربت.

الاستخدام: python3 .kiro/tools/build_preview.py
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "docs", "preview-harness")

HEAD = """<!doctype html>
<html lang="en" dir="{dir}">
<head>
<meta charset="utf-8">
<title>{title}</title>
<link rel="stylesheet" href="{rel}/assets/tokens.css">
<link rel="stylesheet" href="{rel}/assets/base.css">
<link rel="stylesheet" href="{rel}/assets/sadu.css">
<link rel="stylesheet" href="{rel}/assets/ember.css">
<link rel="stylesheet" href="{rel}/assets/sections.css">
<style>
  /* [data-reveal] يبدأ opacity:0 — يُعطَّل في المعاينة وإلّا خرجت اللقطة فارغة */
  html.js [data-reveal], [data-reveal] {{ opacity:1 !important; transform:none !important; }}
  .ico {{ fill:none; stroke:currentColor; stroke-width:1.5;
         stroke-linecap:round; stroke-linejoin:round; }}
  body {{ padding: 0; }}
  .lbl {{ font-family: var(--font-body); font-size: 11px; letter-spacing:.18em;
         color: var(--brass); padding: 10px 14px; border-block-end:1px solid var(--rule); }}
</style>
</head>
<body>
"""


def read_index():
    p = os.path.join(ROOT, "index.html")
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def extract_figures(html):
    """يقتطع كل <figure class="split__art ...> ... </figure>."""
    figs = re.findall(r'(<figure class="split__art.*?</figure>)', html, re.S)
    return figs


def write(name, body, direction="rtl", title="preview"):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(HEAD.format(dir=direction, title=title, rel="../.."))
        fh.write(body)
        fh.write("\n</body>\n</html>\n")
    return path


def main():
    html = read_index()
    figs = extract_figures(html)

    # محاسبة: إن لم يُقتطَع ما نتوقّعه فالفجوةُ في الأداةِ لا في الصفحة
    if len(figs) != 2:
        print(f"خطأ في الأداة: توقّعتُ رسمَين واقتطعتُ {len(figs)}.",
              file=sys.stderr)
        print("إن أُضيف رسمٌ ثالثٌ فحدِّث العدّ صريحاً — ولا تُمرَّر بصمت.",
              file=sys.stderr)
        return 1

    made = []

    # 1) الرسومُ المتجهيّةُ وحدَها — خاليةٌ من النصّ، فاللقطةُ صحيحةٌ تماماً
    made.append(write(
        "art-brazier.html",
        '<div class="lbl">ART 1 / BRAZIER — no text, screenshot is valid</div>'
        '<div style="padding:24px;background:var(--coal-950)">' + figs[0] + "</div>",
        title="art brazier"))

    made.append(write(
        "art-dallah.html",
        '<div class="lbl">ART 2 / DALLAH — no text, screenshot is valid</div>'
        '<div style="padding:24px;background:var(--coal-950)">' + figs[1] + "</div>",
        title="art dallah"))

    # 2) سريرُ الجمر وحدَه — بلا نصّ
    made.append(write(
        "ember-bed.html",
        '<div class="lbl">EMBER BED — generated coals, no text</div>'
        '<section class="stage heat" style="min-block-size:520px">'
        '<span class="mashrabiya"></span><span class="smoke"></span>'
        '<span class="embers" data-embers></span>'
        '<span class="heat__veil"></span></section>'
        '<script src="../../assets/app.js"></script>',
        title="ember bed"))

    # 3) شرائطُ السدو والوَزرة — هندسةٌ بلا نصّ
    made.append(write(
        "sadu.html",
        '<div class="lbl">SADU / NAJDI GEOMETRY — generated, no text</div>'
        '<div style="background:var(--coal-900);padding:34px;display:grid;gap:30px">'
        '<div class="sadu"></div>'
        '<div class="sadu sadu--fine"></div>'
        '<div class="sadu sadu--ember"></div>'
        '<div class="sadu-diamond"></div>'
        '<div class="dado" style="block-size:150px;background:var(--coal-800)"></div>'
        '<div class="dado dado--bone" style="block-size:150px;background:var(--bone)"></div>'
        "</div>",
        title="sadu"))

    # 4) الرموزُ كلّها — بلا نصّ
    symbols = re.findall(r'<symbol id="([^"]+)"', html)
    cells = "".join(
        f'<div style="display:grid;gap:6px;justify-items:center;'
        f'padding:14px;border:1px solid var(--rule);border-radius:6px">'
        f'<svg class="ico" style="inline-size:34px;block-size:34px;'
        f'color:var(--glow)"><use href="#{s}"/></svg>'
        f'<code style="font-size:9px;color:var(--brass);direction:ltr">{s}</code>'
        f"</div>"
        for s in symbols)
    # تُدرَج مجموعةُ الرموزِ كما هي من الأصل
    sprite = re.search(r'(<svg hidden.*?</svg>)', html, re.S)
    made.append(write(
        "icons.html",
        '<div class="lbl">ICON SET — ' + str(len(symbols)) +
        ' symbols, geometric, no imported art</div>' +
        (sprite.group(1) if sprite else "") +
        '<div style="background:var(--coal-900);padding:26px;display:grid;'
        'gap:12px;grid-template-columns:repeat(7,1fr)">' + cells + "</div>",
        title="icons"))

    # 5) صفحةُ اختبارٍ بنصٍّ **لاتيني** — الوحيدةُ التي يصحُّ الحكمُ بها
    #    على التبايُنِ والتخطيطِ والمقاسات، لأنّ الصندوقَ بلا خطوطٍ عربيّة.
    latin = """
<div class="lbl">LATIN TYPE TEST — the only valid basis to judge contrast,
sizing and layout in this sandbox (zero Arabic fonts installed)</div>

<section class="section surface--coal-lit" style="padding-block:46px">
  <div class="wrap">
    <span class="eyebrow">THE IDEA</span>
    <h2 class="title">The ember is the cook</h2>
    <p class="lead">Fire gives flame and soot. Embers give clean steady heat
    that cooks meat from within and leaves it tender, and gives rice a golden
    floor no stove can make. Price 150 QAR — 2026 — digits must be Western.</p>
  </div>
</section>

<section class="section surface--bone dado dado--bone" style="padding-block:46px">
  <div class="wrap">
    <span class="eyebrow">THE RICE</span>
    <h2 class="title">Every Gulf rice</h2>
    <p class="lead">Rice here is not a side dish. 0123456789</p>
    <div class="rice-grid">
      <article class="rice">
        <svg class="ico rice__mark"><use href="#i-pot"/></svg>
        <h3 class="rice__name">Majboos</h3>
        <p class="rice__origin">Kuwait &middot; Bahrain &middot; Qatar</p>
        <p class="rice__desc">Meat simmered in majboos spice, rice cooked in
        its broth until it drinks it. Served with daqoos.</p>
      </article>
      <article class="rice">
        <svg class="ico rice__mark"><use href="#i-rice-dome"/></svg>
        <h3 class="rice__name">Kabsa</h3>
        <p class="rice__origin">Najd &middot; Riyadh</p>
        <p class="rice__desc">Kabsa spice, tomato and black lime, topped with
        toasted almond and raisin.</p>
      </article>
      <article class="rice">
        <svg class="ico rice__mark"><use href="#i-saffron"/></svg>
        <h3 class="rice__name">Bukhari</h3>
        <p class="rice__origin">Hijaz &middot; Makkah</p>
        <p class="rice__desc">Carrot, raisin and a light spice, golden from
        saffron. The calmest of them all.</p>
      </article>
    </div>
  </div>
</section>

<section class="section surface--coal" style="padding-block:46px">
  <div class="wrap">
    <span class="eyebrow">THE GRILL</span>
    <h2 class="title">What deserves the ember</h2>
    <div class="grill-row">
      <article class="grill">
        <svg class="ico grill__mark"><use href="#i-skewer"/></svg>
        <h3 class="grill__name">Ember kebab</h3>
        <p class="grill__desc">Hand-kneaded minced meat with fat, onion and
        parsley, wrapped on the wide skewer.</p>
      </article>
      <article class="grill">
        <svg class="ico grill__mark"><use href="#i-ribs"/></svg>
        <h3 class="grill__name">Lamb chops</h3>
        <p class="grill__desc">Salt and pepper only, high ember, short time.</p>
      </article>
      <article class="grill">
        <svg class="ico grill__mark"><use href="#i-fish"/></svg>
        <h3 class="grill__name">Gulf hamour</h3>
        <p class="grill__desc">Whole fish, scored and rubbed with green
        spice, grilled in a cage over coals.</p>
      </article>
    </div>
  </div>
</section>

<section class="section surface--ash" style="padding-block:46px">
  <div class="wrap">
    <span class="eyebrow">THE TABLE</span>
    <h2 class="title title--h2">From the menu</h2>
    <div class="menu-cols">
      <section class="menu-card">
        <h3 class="menu-card__head"><svg class="ico"><use href="#i-mezze"/></svg>Mezze</h3>
        <ul class="menu-list">
          <li class="menu-item"><div class="menu-item__row">
            <span class="menu-item__name">Daqoos</span>
            <span class="menu-item__fill"></span></div>
            <p class="menu-item__desc">Grilled tomato, garlic and hot pepper</p></li>
          <li class="menu-item"><div class="menu-item__row">
            <span class="menu-item__name">Mutabbal</span>
            <span class="menu-item__fill"></span></div>
            <p class="menu-item__desc">Aubergine straight on the coals</p></li>
          <li class="menu-item"><div class="menu-item__row">
            <span class="menu-item__name">Mixed brazier</span>
            <span class="menu-item__note">to share</span></div>
            <p class="menu-item__desc">A large tray for four to six</p></li>
        </ul>
      </section>
      <section class="menu-card">
        <h3 class="menu-card__head"><svg class="ico"><use href="#i-dallah"/></svg>Coffee</h3>
        <ul class="menu-list">
          <li class="menu-item"><div class="menu-item__row">
            <span class="menu-item__name">Arabic coffee</span>
            <span class="menu-item__note">hospitality</span></div>
            <p class="menu-item__desc">Saffron and cardamom, served before you order</p></li>
          <li class="menu-item"><div class="menu-item__row">
            <span class="menu-item__name">Karak tea</span>
            <span class="menu-item__fill"></span></div>
            <p class="menu-item__desc">Strong, with milk and cardamom</p></li>
        </ul>
      </section>
    </div>
  </div>
</section>

<section class="section surface--coal dado" style="padding-block:46px">
  <div class="wrap contact-grid">
    <div>
      <span class="eyebrow">SOON</span>
      <h2 class="title">Opening soon</h2>
      <p class="lead">Whatever is not decided yet is written here as
      not decided — not invented.</p>
      <div class="hero__actions" style="justify-content:flex-start">
        <a class="btn btn--ember" href="#x">Rice</a>
        <a class="btn" href="#x">Menu</a>
      </div>
    </div>
    <div class="facts">
      <div class="fact"><span class="fact__k">CITY</span>
        <span class="fact__v fact__v--pending">Not announced yet</span></div>
      <div class="fact"><span class="fact__k">OPENING DATE</span>
        <span class="fact__v fact__v--pending">Not set yet</span></div>
      <div class="note"><strong class="note__head">Why these are empty</strong>
      A field that promises certainty while empty is worse than a field that
      says it is empty.</div>
    </div>
  </div>
</section>
"""
    sprite_tag = sprite.group(1) if sprite else ""
    made.append(write("latin-type.html", sprite_tag + latin,
                      direction="ltr", title="latin type test"))

    print(f"بُنيت {len(made)} صفحةَ معاينة في docs/preview-harness/:")
    for m in made:
        print("  " + os.path.relpath(m, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
