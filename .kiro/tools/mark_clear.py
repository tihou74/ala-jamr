#!/usr/bin/env python3
"""يُثبت أنّ كلمةَ الشعارِ لا تَلمس حبرَ الحرفِ الحاضن — رقماً لا رأياً.

لماذا
─────
الشعارُ المطلوب «كلمةُ الجمرِ داخلَ قوسِ العين»، و**حكَمتُ بالعينِ
مرّتين فأخطأتُ المرّتين**: خرجت الكلمةُ فوقَ الرأسِ لا في القوس. ثمّ
قِيس الجوفُ بـ`glyph_hollow.py` فصار الموضعُ صحيحاً — لكنْ بقي سؤالٌ
لا يُجيبه قياسُ الجوفِ وحدَه: **هل تَلمس الكلمةُ الحبرَ فعلاً في
الوضعِ المائلِ أو عند تكبيرِها؟** والمستطيلُ الفارغُ المقيسُ محوريُّ
الأضلاع، والقوسُ منحنٍ، فما خرج منه قد يَسلَم وقد يَلتصق.

وتلاصقُ الحبرِ ليس عيباً نظريّاً: عند الحفرِ على نحاسٍ أو التطريزِ
أو الطبعِ بلونٍ واحدٍ تندمج الكلمةُ بالحرفِ فتصير لطخةً.

كيف
───
تُصوَّر **نفسُ صفحةِ الشعارِ** مرّتين لكلِّ وضع: مرّةً بالحرفِ وحدَه
ومرّةً بالكلمةِ وحدَها (`?v=..&only=..`). ثمّ يُقاس تقاطعُ قناعَي
الحبر. صفرٌ = خلوصٌ تامّ.

> ولا تُعاد هندسةُ الشعارِ في هذه الأداة: تُقاس الصفحةُ التي تُعرَض
> على المالكِ بعينِها. وأداةُ قياسٍ تُعيد بناءَ ما تقيسه تُبارك
> نفسَها — وقع هذا في المشروعِ قبلاً في أداةِ لقطةِ الأقسام.

الاستخدام
─────────
    python3 .kiro/tools/mark_clear.py docs/preview-harness/logo-ain.html a b c d
    python3 .kiro/tools/mark_clear.py --selftest
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import imgdown  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
W = H = 700
# بُعدٌ لونيٌّ عن لونِ السطحِ يُعَدُّ بعدَه البكسلُ حبراً. 48 يَتجاوز
# حوافَّ التنعيمِ (anti-aliasing) ولا يَتجاوز لوناً مقصوداً: أقربُ
# زوجٍ في لوحةِ المالكِ (العنابيُّ والفحميُّ) بُعدُهما 78.
TOL = 48


def mask_from_pixels(px, w, h, nch, tol=TOL):
    """الحبرُ = ما يَبعُد عن لونِ الخلفيّةِ، لا «ما كان فاتحاً».

    ⚠️ **ولماذا تغيّر هذا:** كانت القاعدةُ `أيُّ قناةٍ ≥ 110 حبرٌ` —
    أي **افتراضُ حبرٍ أبيضَ على سطحٍ داكن**. وطلب المالكُ موديلاً
    عنابيّاً، وموضعُه الطبيعيُّ سطحٌ **كريميٌّ فاتح** — فانقلب
    القطبُ: صارت الخلفيّةُ كلُّها «حبراً» والحرفُ «فراغاً»، وأخرجت
    الأداةُ **تلاصقاً في 476 ألفَ بكسل** على علامةٍ سليمةٍ تماماً.

    > وهذا نوعٌ ثانٍ من عَوَرِ الحوارس: الأوّلُ يُبارك ما لم يفحصه،
    > وهذا **يُسقِط السليمَ** لأنّ فرضاً مخفيّاً فيه (لونُ السطح)
    > لم يُكتَب شرطاً. فالفرضُ يُستخرَج من الصورةِ لا يُفترَض:
    > أكثرُ لونٍ تكراراً هو السطح، وما بَعُد عنه حبرٌ. وتصحّ على
    > الأبيضِ والعنابيِّ والذهبيِّ وعلى أيِّ سطحٍ يَختاره."""
    counts = {}
    step = max(1, (w * h) // 20000)       # عيّنةٌ تكفي لإيجادِ السطح
    for i in range(0, w * h, step):
        o = i * nch
        key = (px[o], px[o + 1], px[o + 2])
        counts[key] = counts.get(key, 0) + 1
    br, bg_, bb = max(counts, key=counts.get)

    m = bytearray(w * h)
    t2 = tol * tol
    for i in range(w * h):
        o = i * nch
        dr = px[o] - br
        dg = px[o + 1] - bg_
        db = px[o + 2] - bb
        if dr * dr + dg * dg + db * db > t2:
            m[i] = 1
    return m, (br, bg_, bb)


def _mask(path):
    px, w, h, nch = imgdown.decode_png(path)
    m, _bg = mask_from_pixels(px, w, h, nch)
    return m, w, h


def overlap(m1, m2):
    return sum(1 for a, b in zip(m1, m2) if a and b)


def bbox(m, w, h):
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        row = y * w
        for x in range(w):
            if m[row + x]:
                x0 = min(x0, x); x1 = max(x1, x)
                y0 = min(y0, y); y1 = max(y1, y)
    return None if x1 < 0 else (x0, y0, x1, y1)


def contained(inner, outer):
    """هل حدُّ حبرِ الكلمةِ داخلَ حدِّ حبرِ الحرفِ الحاضن؟

    **ولماذا هذا الفحصُ لازمٌ مع فحصِ التلاصق:** الخلوصُ وحدَه يَصدُق
    صدقاً كاملاً على كلمةٍ **خارجَ القوسِ تماماً** — بل هو أصدقُ ما
    يكون عليها. ووقع هذا حرفيّاً: خاصّيّةٌ منطقيّةٌ (`inset-inline-end`)
    وضعت الكلمةَ على الجهةِ المقابلةِ في صفحةٍ عربيّةٍ، فخرجت من
    العلامةِ كلِّها **ومرّ الحارسُ أخضرَ**. فالمطلوبُ شرطان: لا
    تَلمس، **وتكون في الداخل**."""
    if inner is None or outer is None:
        return False
    return (outer[0] <= inner[0] and inner[2] <= outer[2]
            and outer[1] <= inner[1] and inner[3] <= outer[3])


def dilate(m, w, h, r):
    """يُسمَّن القناعُ بـr بكسلاً: التلاصقُ عيبٌ كالتقاطعِ تماماً.

    حرفان بينهما بكسلٌ واحدٌ يُقرآن ملتصقَين في الطباعةِ وفي أيِّ
    تصغير. فيُقاس **الخلوصُ** لا التقاطعُ وحدَه."""
    if r <= 0:
        return m
    out = bytearray(m)
    for _ in range(r):
        cur = bytearray(out)
        for y in range(h):
            row = y * w
            for x in range(w):
                if cur[row + x]:
                    continue
                if ((x and cur[row + x - 1]) or (x + 1 < w and cur[row + x + 1])
                        or (y and cur[row - w + x])
                        or (y + 1 < h and cur[row + w + x])):
                    out[row + x] = 1
    return out


def shoot(html, out, query):
    url = "file://" + os.path.abspath(html) + "?" + query
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "shoot.py"), url, out,
         str(W), str(H), "2400"], capture_output=True, text=True)
    if not os.path.isfile(out):
        sys.stderr.write(r.stdout + r.stderr)
        return False
    return True


def check(html, variants, gap):
    tmpdir = os.path.join(ROOT, "docs", "preview", "v9")
    os.makedirs(tmpdir, exist_ok=True)
    worst = 0
    print(f"خلوصُ الكلمةِ عن حبرِ الحرف · هامشُ أمانٍ {gap} بكسل "
          f"(على إطارِ {W}px)")
    for v in variants:
        pa = os.path.join(tmpdir, f".clear-{v}-ain.png")
        pj = os.path.join(tmpdir, f".clear-{v}-jamr.png")
        if not (shoot(html, pa, f"v={v}&only=ain")
                and shoot(html, pj, f"v={v}&only=jamr")):
            print(f"  {v}: فشل الرسم")
            worst = max(worst, 1)
            continue
        ma, w, h = _mask(pa)
        mj, _, _ = _mask(pj)
        if not any(ma) or not any(mj):
            print(f"  {v}: ⚠️  أحدُ الطرفين بلا حبرٍ — العزلُ لم يعمل")
            worst = max(worst, 1)
        else:
            hit = overlap(dilate(ma, w, h, gap), mj)
            inside = contained(bbox(mj, w, h), bbox(ma, w, h))
            bits = []
            bits.append("✓ خلوصٌ تامّ" if hit == 0
                        else f"✗ تلاصقٌ في {hit} بكسل")
            bits.append("✓ داخلَ العلامة" if inside
                        else "✗ **خارجَ حدِّ الحرفِ** — ليست في القوس")
            print(f"  {v}: {' · '.join(bits)}")
            worst = max(worst, 1 if (hit or not inside) else 0)
        os.remove(pa)
        os.remove(pj)
    return worst


def selftest():
    ok = True

    def c(label, got, want):
        nonlocal ok
        good = got == want
        if not good:
            ok = False
        print(f"  [{'PASS' if good else 'FAIL'}] {label}"
              f"{'' if good else f' (كان {got} والمنتظر {want})'}")

    w = h = 9
    a = bytearray(w * h)
    b = bytearray(w * h)
    a[4 * w + 2] = 1          # حبرٌ عند (2,4)
    b[4 * w + 4] = 1          # وحبرٌ عند (4,4) — بينهما بكسلٌ فارغ
    c("منفصلان: لا تقاطع", overlap(a, b), 0)
    c("هامشٌ 1 لا يكفي للتلاصق", overlap(dilate(a, w, h, 1), b), 0)
    c("هامشٌ 2 يَكشف القُربَ", overlap(dilate(a, w, h, 2), b), 1)
    same = bytearray(a)
    c("المتطابقُ يُكشَف فوراً", overlap(a, same), 1)
    c("التسمينُ بصفرٍ لا يُغيّر", overlap(dilate(a, w, h, 0), b), 0)

    # ══ الاحتواءُ ══════════════════════════════════════════════
    # **والحالةُ الحاسمةُ أوّلاً**: منفصلان تماماً ⇒ خلوصُهما تامٌّ
    # والاحتواءُ **مكذوب**. وهي بعينُها الحالةُ التي مرّت أخضرَ.
    out = bytearray(w * h)
    for y in range(2, 8):
        for x in range(2, 8):
            out[y * w + x] = 1
    inn = bytearray(w * h)
    for y in range(3, 6):
        for x in range(3, 6):
            inn[y * w + x] = 1
    far = bytearray(w * h)
    far[1 * w + 8] = 1
    c("الداخلُ يُقرأ محتوى", contained(bbox(inn, w, h), bbox(out, w, h)), True)
    c("البعيدُ لا يُقرأ محتوى", contained(bbox(far, w, h), bbox(out, w, h)), False)
    c("البعيدُ خالصٌ مع ذلك (فالخلوصُ لا يكفي)",
      overlap(dilate(out, w, h, 1), far), 0)
    c("الفارغُ لا يُقرأ محتوى", contained(None, bbox(out, w, h)), False)

    # ══ القطبُ يُستخرَج لا يُفترَض ═══════════════════════════════
    # والحالةُ الحاسمةُ هي **المقلوبة**: علامةٌ عنابيّةٌ على سطحٍ
    # كريميّ. القاعدةُ القديمةُ («الفاتحُ حبرٌ») تَعُدُّ السطحَ كلَّه
    # حبراً فتُسقِط علامةً سليمة — ووقع هذا فعلاً بـ476 ألفَ بكسل.
    def synth(bg, fg, n_fg):
        px = bytearray()
        for i in range(36):
            c3 = fg if i < n_fg else bg
            px += bytes(c3)
        return px

    CREAM, BURG, CHAR, WHITE = ((230, 226, 218), (93, 30, 33),
                                (16, 17, 17), (255, 255, 255))
    m1, bg1 = mask_from_pixels(synth(CREAM, BURG, 5), 6, 6, 3)
    c("سطحٌ كريميٌّ: السطحُ يُعرَف", bg1, CREAM)
    c("وحبرُه العنابيُّ 5 بكسل", sum(m1), 5)
    m2, bg2 = mask_from_pixels(synth(CHAR, WHITE, 7), 6, 6, 3)
    c("سطحٌ فحميّ: السطحُ يُعرَف", bg2, CHAR)
    c("وحبرُه الأبيضُ 7 بكسل", sum(m2), 7)
    # ولا يُعَدُّ تنعيمُ الحروفِ حبراً كاملاً ولا يُهمَل لونٌ مقصود
    near = (16 + 20, 17 + 20, 17 + 20)
    m3, _ = mask_from_pixels(synth(CHAR, near, 4), 6, 6, 3)
    c("فرقٌ 20 لا يُعَدُّ حبراً (تنعيم)", sum(m3), 0)
    m4, _ = mask_from_pixels(synth(CHAR, BURG, 4), 6, 6, 3)
    c("والعنابيُّ على الفحميِّ يُعَدُّ حبراً", sum(m4), 4)
    return 0 if ok else 2


def main(argv):
    if "--selftest" in argv:
        return selftest()
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 1
    html = args[0] if os.path.isabs(args[0]) else os.path.join(ROOT, args[0])
    if not os.path.isfile(html):
        print(f"مرفوض: لا صفحةَ عند {html}", file=sys.stderr)
        return 1
    variants = args[1:] or ["a"]
    gap = 2
    for i, a in enumerate(argv):
        if a == "--gap" and i + 1 < len(argv):
            gap = int(argv[i + 1])
    return check(html, variants, gap)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
