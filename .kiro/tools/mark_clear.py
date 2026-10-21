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
INK_MIN = 110


def _mask(path):
    px, w, h, nch = imgdown.decode_png(path)
    m = bytearray(w * h)
    for i in range(w * h):
        if px[i * nch] >= INK_MIN:
            m[i] = 1
    return m, w, h


def overlap(m1, m2):
    return sum(1 for a, b in zip(m1, m2) if a and b)


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
            mark = "✓ خلوصٌ تامّ" if hit == 0 else f"✗ تلاصقٌ في {hit} بكسل"
            print(f"  {v}: {mark}")
            worst = max(worst, 1 if hit else 0)
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
