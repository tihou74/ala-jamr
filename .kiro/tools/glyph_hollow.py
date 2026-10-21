#!/usr/bin/env python3
"""يقيسُ جوفَ المحرفِ: أكبرُ مستطيلٍ فارغٍ داخلَ حدِّ حبرِ الحرف.

لماذا هذه الأداةُ موجودة
────────────────────────
طلب المالكُ شعاراً «العينُ كبيرةٌ وكلمةُ الجمرِ داخلَ قوسِ العين».
فوضعتُ الكلمةَ **بالتخمينِ البصريّ** مرّتين، وسقطت المرّتان: خرجت
الكلمةُ فوقَ رأسِ العينِ لا في قوسِها. والسببُ أنّ موضعَ الجوفِ
خاصّيّةٌ في **رسمِ المحرفِ** لا في تقديري، ويتغيّر بتغيُّرِ الحرفِ
والوزنِ والخطّ.

وأخطرُ من سقوطِ المرّتين أنّ التخمينَ **يبدو صحيحاً في لقطةٍ واحدةٍ
ثمّ ينكسر عند تغييرِ المقاس**: نسبةٌ مكتوبةٌ بالتجربةِ على مربّعٍ
بعينِه لا تصحّ على مربّعٍ آخر. فيُقاس الجوفُ **منسوباً إلى حدِّ حبرِ
الحرفِ نفسِه**، وتُشتقُّ منه إحداثيّاتُ CSS بوحدةِ `em` — فتصحّ على
كلِّ مقاس.

ما تُخرجه
─────────
  · حدُّ حبرِ الحرف (ink bbox) بالبكسلِ وبالـem
  · أكبرُ ثلاثةِ مستطيلاتٍ فارغةٍ داخلَ الحدّ، كلُّ واحدٍ بمركزِه
    وسِعتِه بالـem — والثلاثةُ لا واحدٌ **بقصد**: «أكبرُ فارغٍ» ليس
    دائماً «الجوفَ المقصود» (قد يكون فراغاً خارجَ القوس)، فتُعرَض
    المرشّحاتُ مرسومةً على الصورةِ ليُحكَم بالعينِ مرّةً واحدةً ثمّ
    يُثبَّت الرقم.
  · صورةٌ فيها المستطيلاتُ مرسومةً فوق الحرف

الاستخدام
─────────
    python3 .kiro/tools/glyph_hollow.py ع
    python3 .kiro/tools/glyph_hollow.py ع --weight 700 --out docs/preview/v9/h.png
    python3 .kiro/tools/glyph_hollow.py --selftest
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import imgdown  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
# المربّعُ ضِعفُ مقاسِ الخطِّ تقريباً: يَسَعُ الحرفَ وذيلَه بلا قطع.
# والقطعُ يُفقِد القياسَ معناه — فيُفحَص بعد الرسمِ لا يُفترَض.
BOX = 640
FONT_PX = 300
INK_MIN = 110          # الحرفُ أبيضُ على فحميّ: أيُّ قناةٍ فوق هذا حبرٌ
MARK_COLORS = [(166, 130, 74), (21, 66, 48), (93, 30, 33)]


def _html(glyph, family, weight, fontfile):
    """صفحةٌ واحدةُ الحرفِ بتخطيطٍ ثابتٍ معلومٍ — لا هامشَ ولا إزاحة.

    التخطيطُ هنا **هو** التخطيطُ الذي يُستعمل في الشعار، وإلّا
    فالنِّسَبُ المقيسةُ لا تنطبق على ما يُرسَم فعلاً."""
    return f"""<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><style>
@font-face{{font-family:"M";font-weight:{weight};font-display:block;
  src:url(file://{fontfile}) format("truetype")}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{BOX}px;height:{BOX}px;background:#101111;overflow:hidden}}
.g{{position:absolute;inset:0;display:grid;place-items:center;
   font:{weight} {FONT_PX}px/1.5 "M",serif;color:#fff}}
</style></head><body><div class="g">{glyph}</div></body></html>"""


def ink_mask(path):
    px, w, h, nch = imgdown.decode_png(path)
    mask = bytearray(w * h)
    for i in range(w * h):
        if px[i * nch] >= INK_MIN:
            mask[i] = 1
    return mask, w, h


def ink_bbox(mask, w, h):
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        row = y * w
        for x in range(w):
            if mask[row + x]:
                if x < x0:
                    x0 = x
                if x > x1:
                    x1 = x
                if y < y0:
                    y0 = y
                if y > y1:
                    y1 = y
    if x1 < 0:
        return None
    return x0, y0, x1, y1


def largest_empty(mask, w, bbox):
    """أكبرُ مستطيلٍ خالٍ من الحبرِ داخلَ الحدّ — بمدرَّجِ الأعمدة.

    لكلِّ صفٍّ يُحتفَظ بطولِ عمودِ الفراغِ المنتهي عنده، ثمّ يُحَلّ
    «أكبرُ مستطيلٍ في مدرَّج» بمِكدَسٍ. O(عدد البكسل)."""
    x0, y0, x1, y1 = bbox
    bw = x1 - x0 + 1
    heights = [0] * bw
    best = (0, 0, 0, 0, 0)       # area, left, top, right, bottom
    for y in range(y0, y1 + 1):
        row = y * w
        for i in range(bw):
            heights[i] = 0 if mask[row + x0 + i] else heights[i] + 1
        stack = []
        for i in range(bw + 1):
            cur = heights[i] if i < bw else 0
            start = i
            while stack and stack[-1][1] >= cur:
                si, sh = stack.pop()
                area = sh * (i - si)
                if area > best[0]:
                    best = (area, x0 + si, y - sh + 1, x0 + i - 1, y)
                start = si
            stack.append((start, cur))
    return best


def hollows(mask, w, h, bbox, count=3):
    """المرشّحاتُ الأولى: يُحسَب الأكبرُ ثمّ يُشطَب فيُحسَب التالي."""
    work = bytearray(mask)
    out = []
    for _ in range(count):
        area, lx, ty, rx, by = largest_empty(work, w, bbox)
        if area <= 0:
            break
        out.append((area, lx, ty, rx, by))
        for y in range(ty, by + 1):
            row = y * w
            for x in range(lx, rx + 1):
                work[row + x] = 1
    return out


def draw(path, out, rects):
    px, w, h, nch = imgdown.decode_png(path)
    for i, (_, lx, ty, rx, by) in enumerate(rects):
        r, g, b = MARK_COLORS[i % len(MARK_COLORS)]
        for x in range(lx, rx + 1):
            for y in (ty, by):
                o = (y * w + x) * nch
                px[o], px[o + 1], px[o + 2] = r, g, b
        for y in range(ty, by + 1):
            for x in (lx, rx):
                o = (y * w + x) * nch
                px[o], px[o + 1], px[o + 2] = r, g, b
    imgdown.encode_png(out, px, w, h, nch)


def report(glyph, family, weight, fontfile, out):
    tmp_html = os.path.join(ROOT, "docs", "preview-harness", ".glyph-tmp.html")
    tmp_png = os.path.join(ROOT, "docs", "preview", "v9", ".glyph-tmp.png")
    os.makedirs(os.path.dirname(tmp_html), exist_ok=True)
    with open(tmp_html, "w", encoding="utf-8") as fh:
        fh.write(_html(glyph, family, weight, fontfile))

    rc = subprocess.run(
        [sys.executable, os.path.join(HERE, "shoot.py"), tmp_html, tmp_png,
         str(BOX), str(BOX), "2200"], capture_output=True, text=True)
    if not os.path.isfile(tmp_png):
        print(rc.stdout + rc.stderr, file=sys.stderr)
        print("فشل: لم تُرسَم صورةُ الحرف.", file=sys.stderr)
        return 1

    mask, w, h = ink_mask(tmp_png)
    bb = ink_bbox(mask, w, h)
    if bb is None:
        print("فشل: لا حبرَ في الصورة — الخطُّ لم يُحمَّل أو الحرفُ فارغ.",
              file=sys.stderr)
        return 2
    x0, y0, x1, y1 = bb

    # القطعُ يُفقِد القياسَ معناه، فيُفحَص صريحاً لا يُفترَض
    touch = [n for n, c in (("أعلى", y0 == 0), ("أسفل", y1 == h - 1),
                            ("يمين", x1 == w - 1), ("يسار", x0 == 0)) if c]
    if touch:
        print(f"⚠️  الحرفُ يلمس حدَّ الإطار ({' · '.join(touch)}) — "
              f"قد يكون مقطوعاً، فالقياسُ مشكوكٌ فيه.", file=sys.stderr)

    em = FONT_PX
    print(f"الحرف «{glyph}» · {family} · وزن {weight} · "
          f"مقاس {FONT_PX}px في مربّع {BOX}px")
    print(f"حدُّ الحبر: {x1 - x0 + 1}x{y1 - y0 + 1} بكسل = "
          f"{(x1 - x0 + 1) / em:.3f}em x {(y1 - y0 + 1) / em:.3f}em")
    print()
    rects = hollows(mask, w, h, bb)
    for i, (area, lx, ty, rx, by) in enumerate(rects, 1):
        rw, rh = rx - lx + 1, by - ty + 1
        # المركزُ منسوباً إلى حدِّ الحبرِ: من يمينِ الحدِّ ومن أعلاه
        cx = (lx + rx) / 2
        cy = (ty + by) / 2
        print(f"  مرشّح {i} · {rw}x{rh} بكسل = {rw / em:.3f}em x {rh / em:.3f}em")
        print(f"      مركزُه من يمينِ حدِّ الحبر: "
              f"{(x1 - cx) / em:.3f}em ({(x1 - cx) / (x1 - x0) * 100:.1f}% من عرضِه)")
        print(f"      مركزُه من أعلى حدِّ الحبر: "
              f"{(cy - y0) / em:.3f}em ({(cy - y0) / (y1 - y0) * 100:.1f}% من ارتفاعِه)")
        # ══ الجسرُ إلى CSS ══════════════════════════════════════════
        # النسبةُ من حدِّ الحبرِ لا تُكتب في CSS مباشرةً: المتصفّحُ لا
        # يعرف حدَّ الحبر. فتُخرَج النسبةُ **من مربّعِ المعايرةِ** —
        # ومن استعمل نفسَ التخطيطِ (مربّعٌ 2.133em · خطٌّ 1em/1.5 ·
        # grid place-items:center) تنطبق عليه حرفاً.
        print(f"      ⇒ CSS على مربّعِ {BOX / FONT_PX:.3f}em: "
              f"inset-inline-end:{(w - cx) / w * 100:.1f}% · "
              f"top:{cy / h * 100:.1f}%")
    if out:
        draw(tmp_png, out, rects)
        print(f"\n  -> {os.path.relpath(out, ROOT)} (المرشّحاتُ مرسومةٌ: "
              f"ذهبيٌّ 1 · أخضرُ 2 · بُرغنديٌّ 3)")
    os.remove(tmp_html)
    os.remove(tmp_png)
    return 0


def selftest():
    """الأداةُ تُجرَّب على قناعٍ معلومِ الجوابِ لا على حرفٍ حقيقيّ."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        good = got == want
        if not good:
            ok = False
        print(f"  [{'PASS' if good else 'FAIL'}] {label}"
              f"{'' if good else f' (كان {got} والمنتظر {want})'}")

    # إطارٌ من الحبرِ بجوفٍ فارغٍ معلومِ المقاس: 10..19 أفقياً و5..14 رأسياً
    w = h = 30
    m = bytearray(w * h)
    for y in range(3, 20):
        for x in range(8, 22):
            m[y * w + x] = 1
    for y in range(5, 15):
        for x in range(10, 20):
            m[y * w + x] = 0
    bb = ink_bbox(m, w, h)
    check("حدُّ الحبرِ يُقاس بدقّة", bb, (8, 3, 21, 19))
    area, lx, ty, rx, by = largest_empty(m, w, bb)
    check("أكبرُ فراغٍ يُصاب تماماً", (lx, ty, rx, by), (10, 5, 19, 14))
    check("مساحتُه صحيحة", area, 100)

    # صورةٌ بلا حبرٍ: يُرجَع None لا يُنهار
    check("قناعٌ فارغٌ يُرجِع None", ink_bbox(bytearray(w * h), w, h), None)

    # جوفان: الأكبرُ أوّلاً ثمّ الذي بعده — لا يتكرّر نفسُه
    m2 = bytearray(b"\x01" * (w * h))
    for y in range(2, 12):
        for x in range(2, 12):
            m2[y * w + x] = 0
    for y in range(16, 22):
        for x in range(16, 22):
            m2[y * w + x] = 0
    got = [(r[1], r[2], r[3], r[4]) for r in hollows(m2, w, h, (0, 0, 29, 29), 2)]
    check("الجوفُ الأكبرُ أوّلاً", got[0], (2, 2, 11, 11))
    check("والثاني غيرُه لا نفسُه", got[1], (16, 16, 21, 21))
    return 0 if ok else 2


def main(argv):
    if "--selftest" in argv:
        return selftest()
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 1
    glyph = args[0]
    weight = "700"
    family = "Aref Ruqaa"
    fontfile = os.path.join(ROOT, "assets", "fonts", "ArefRuqaa-Bold.ttf")
    out = None
    for i, a in enumerate(argv):
        if a == "--weight" and i + 1 < len(argv):
            weight = argv[i + 1]
            if weight == "400":
                fontfile = os.path.join(ROOT, "assets", "fonts",
                                        "ArefRuqaa-Regular.ttf")
        if a == "--out" and i + 1 < len(argv):
            out = os.path.abspath(os.path.join(ROOT, argv[i + 1]))
    if not os.path.isfile(fontfile):
        print(f"مرفوض: لا خطَّ عند {fontfile}", file=sys.stderr)
        return 1
    return report(glyph, family, weight, fontfile, out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
