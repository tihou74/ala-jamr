#!/usr/bin/env python3
"""قياسُ سطوعِ منطقةٍ من لقطةٍ ونسبةِ تبايُنِها — رقمٌ لا انطباع.

لماذا: صورُ المالكِ أسطحٌ خلفيّةٌ يُكتَب عليها. والحكمُ بالعينِ على
«هل النصُّ مقروءٌ فوق هذه الصورة؟» يخدع مرّتين: اللقطةُ تُصغَّر عند
العرضِ فيبدو الباهتُ مقبولاً، والعينُ تُكمل الحروفَ التي لا تراها.
فيُقاس السطوعُ الفعليُّ تحت النصِّ وتُحسَب نسبةُ التبايُنِ بمعادلةِ
WCAG، ويُقارَن بالحدِّ 4.5 للنصِّ العاديِّ و3.0 للكبير.

**وهذه أداةُ قياسٍ لا حارس**: لا تُسمّى `check_*.py` لأنّها تحتاج لقطةً
مولَّدةً مسبقاً، ولا يصحُّ أن تُسقِط النشرَ إن غابت اللقطة. وحارسٌ
يُسقِط النشرَ لغيابِ ملفٍّ مؤقّتٍ يُعطَّل بعد حين.

الاستخدام:
    python3 .kiro/tools/measure_luma.py <img.png> <x> <y> <w> <h> [--fg \\#F3EDE3]
    python3 .kiro/tools/measure_luma.py --selftest
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import imgdown  # noqa: E402


def _lin(c):
    """قناةٌ من 0..255 إلى خطّيّةٍ كما تنصُّ WCAG."""
    s = c / 255.0
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def luminance(r, g, b):
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(l1, l2):
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def hex_luma(h):
    h = h.lstrip("#")
    return luminance(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def measure(src, x, y, w, h, fg="#F3EDE3"):
    pixels, W, H, nch = imgdown.decode_png(src)
    x = max(0, min(int(x), W - 1))
    y = max(0, min(int(y), H - 1))
    w = max(1, min(int(w), W - x))
    h = max(1, min(int(h), H - y))

    lums = []
    for yy in range(y, y + h):
        row = yy * W * nch
        for xx in range(x, x + w):
            p = row + xx * nch
            if nch >= 3:
                lums.append(luminance(pixels[p], pixels[p + 1], pixels[p + 2]))
            else:
                lums.append(luminance(pixels[p], pixels[p], pixels[p]))
    lums.sort()
    n = len(lums)

    def pct(q):
        return lums[min(n - 1, int(q * n))]

    fgl = hex_luma(fg)
    # النصُّ فوق خلفيّةٍ متفاوتة: **أسوأُ موضعٍ هو الحاكم**، لا المتوسّط.
    # ومتوسّطٌ مقبولٌ يُخفي بقعةً ساطعةً يختفي عليها سطرٌ كامل.
    worst_bg = pct(0.95) if fgl > 0.5 else pct(0.05)
    res = {
        "n": n,
        "min": lums[0],
        "p05": pct(0.05),
        "median": pct(0.5),
        "p95": pct(0.95),
        "max": lums[-1],
        "fg": fgl,
        "contrast_median": contrast(fgl, pct(0.5)),
        "contrast_worst": contrast(fgl, worst_bg),
    }
    print(f"  منطقة {w}x{h} عند ({x},{y}) من {os.path.basename(src)}")
    print(f"  سطوعُ الخلفيّة: أدنى {res['min']:.3f} · وسيط "
          f"{res['median']:.3f} · أعلى {res['max']:.3f}")
    print(f"  تبايُنُ النصِّ ({fg}): وسيطٌ {res['contrast_median']:.2f}:1 · "
          f"**أسوأُ موضعٍ {res['contrast_worst']:.2f}:1**")
    verdict = ("يكفي للعاديِّ والكبير" if res["contrast_worst"] >= 4.5 else
               "يكفي للكبيرِ فقط" if res["contrast_worst"] >= 3.0 else
               "لا يكفي")
    print(f"  الحكمُ على أسوأِ موضع: {verdict} (الحدّ 4.5 عاديّ · 3.0 كبير)")
    return res


def selftest():
    fails = []

    def ok(cond, label):
        print(("  PASS  " if cond else "  FAIL  ") + label)
        if not cond:
            fails.append(label)

    # 1) قيمٌ معروفةٌ من المعيار: أبيضُ على أسودَ = 21:1 بالضبط
    ok(abs(contrast(hex_luma("#FFFFFF"), hex_luma("#000000")) - 21.0) < 0.01,
       "أبيضُ على أسودَ = 21:1")
    ok(abs(contrast(hex_luma("#FFFFFF"), hex_luma("#FFFFFF")) - 1.0) < 0.001,
       "لونٌ على نفسِه = 1:1")
    # #767676 على الأبيضِ = 4.54:1 في جداولِ WCAG المنشورة
    r = contrast(hex_luma("#767676"), hex_luma("#FFFFFF"))
    ok(4.4 < r < 4.7, f"رمادي 767676 على أبيض = {r:.2f}:1 (المنشور 4.54)")

    tmp = os.path.abspath(os.path.join(HERE, "..", "..", ".tmp"))
    os.makedirs(tmp, exist_ok=True)

    # 2) يُقرأ السطوعُ من الموضعِ المطلوبِ فعلاً — لا من مجاوره
    p = os.path.join(tmp, "luma-src.png")
    W = H = 40
    px = bytearray(W * H * 3)
    for yy in range(H):
        for xx in range(W):
            v = 255 if xx >= 20 else 0
            i = (yy * W + xx) * 3
            px[i] = px[i + 1] = px[i + 2] = v
    imgdown.encode_png(p, px, W, H, 3)

    black = measure(p, 0, 0, 10, 10)
    ok(black["median"] < 0.001, "النصفُ الأسودُ سطوعُه صفر")
    white = measure(p, 25, 0, 10, 10)
    ok(white["median"] > 0.99, "النصفُ الأبيضُ سطوعُه واحد")
    ok(black["n"] == 100, f"عُدَّت 100 بكسلٍ فعلاً (كانت {black['n']})")

    # 3) **الحاكمُ أسوأُ موضعٍ لا الوسيط** — وهذه هي الحالةُ الواقعيّة:
    #    صورةٌ معتمةٌ في عمومِها وفيها بقعةٌ ساطعةٌ صغيرة (وميضُ لهبٍ أو
    #    صحنٌ أبيض). الوسيطُ يقول «مقروء» والبقعةُ يختفي عليها سطرٌ كامل.
    #    وأوّلُ فيكستشر كتبتُه كان نصفاً أبيضَ ونصفاً أسودَ، **فكان
    #    الوسيطُ نفسُه أبيضَ** فلم يُفرّق التأكيدُ شيئاً وسقط. فالفيكستشرُ
    #    يُصحَّح ولا يُضعَّف التأكيد: البقعةُ 10% لا 50%.
    q = os.path.join(tmp, "luma-spot.png")
    px2 = bytearray(W * H * 3)  # أسودُ كلُّه
    for yy in range(H):
        for xx in range(36, 40):  # عمودٌ ساطعٌ = 10% من العرض
            i = (yy * W + xx) * 3
            px2[i] = px2[i + 1] = px2[i + 2] = 255
    imgdown.encode_png(q, px2, W, H, 3)

    spot = measure(q, 0, 0, 40, 40, fg="#F3EDE3")
    ok(spot["median"] < 0.001, "الوسيطُ معتمٌ (الصورةُ معتمةٌ في عمومِها)")
    ok(spot["contrast_median"] > 15,
       f"الوسيطُ يقول (مقروء): {spot['contrast_median']:.1f}:1")
    ok(spot["contrast_worst"] < 1.5,
       f"وأسوأُ موضعٍ يقول (يختفي): {spot['contrast_worst']:.2f}:1")
    ok(spot["contrast_worst"] < spot["contrast_median"] / 10,
       "أسوأُ موضعٍ أقسى من الوسيطِ بعشرةِ أضعافٍ — فلا يُخفيه المتوسّط")

    print(f"\n{'سقط ' + str(len(fails)) if fails else 'كلُّ فحوصِ القياسِ خضراء'}")
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    a = [v for v in sys.argv[1:] if not v.startswith("--")]
    if len(a) < 5:
        print(__doc__)
        sys.exit(1)
    fg = "#F3EDE3"
    if "--fg" in sys.argv:
        fg = sys.argv[sys.argv.index("--fg") + 1]
    measure(a[0], a[1], a[2], a[3], a[4], fg)
