#!/usr/bin/env python3
"""قَصُّ منطقةٍ من لقطةٍ وتكبيرُها — للحكمِ على تفصيلٍ لا على صفحة.

لماذا: اللقطةُ بعرضِ 1280 تُصغَّر عند العرضِ فيضيع التصادمُ بين سطرَين
أو تماسُّ وسمٍ بخطٍّ منقَّط. والقصُّ يُظهر التفصيلَ بحجمِه الحقيقيِّ
أو مُضاعَفاً، فيُحكَم على ما يُرى لا على ما يُظنّ.

والحدُّ (2000 بكسل) يُفرَض **مرّتين**: حساباً قبل الكتابة، وقياساً
بـimgguard بعدها. والتكبيرُ هو الخطرُ هنا: قصّةٌ بعرضِ 1100 بتكبيرٍ
مزدوجٍ = 2200 ⇒ تتجاوز الحدَّ وتُسقِط الجلسةَ عند القراءة.

الاستخدام:
    python3 .kiro/tools/crop.py <in.png> <out.png> <x> <y> <w> <h> [--zoom N]
    python3 .kiro/tools/crop.py --selftest
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import imgdown  # noqa: E402  — فكُّ PNG وترميزُه بلا Pillow
import imgguard  # noqa: E402

MAX_DIM = 2000


def crop(src, dst, x, y, w, h, zoom=1):
    pixels, W, H, nch = imgdown.decode_png(src)

    # القصُّ يُقصَر على حدودِ الصورة: قصّةٌ خارجَ الإطارِ تُنتج صفوفاً
    # سوداءَ تُقرأ «عطلاً في التصميم» وهي عطلٌ في أمرِ القصّ.
    x = max(0, min(int(x), W - 1))
    y = max(0, min(int(y), H - 1))
    w = max(1, min(int(w), W - x))
    h = max(1, min(int(h), H - y))
    zoom = max(1, int(zoom))

    out_w, out_h = w * zoom, h * zoom
    if out_w > MAX_DIM or out_h > MAX_DIM:
        print(f"مرفوض: الناتجُ {out_w}x{out_h} يتجاوز {MAX_DIM} بكسل.",
              file=sys.stderr)
        print(f"  القصّةُ {w}x{h} بتكبيرِ {zoom}. صغِّر القصّةَ أو التكبير.",
              file=sys.stderr)
        return 2

    out = bytearray(out_w * out_h * nch)
    for oy in range(out_h):
        sy = y + oy // zoom
        src_row = (sy * W) * nch
        dst_row = (oy * out_w) * nch
        for ox in range(out_w):
            sx = x + ox // zoom
            sp = src_row + sx * nch
            dp = dst_row + ox * nch
            out[dp:dp + nch] = pixels[sp:sp + nch]

    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    imgdown.encode_png(dst, out, out_w, out_h, nch)

    # لا يُعتمَد على الحساب: تُقاس الصورةُ المكتوبةُ فعلاً بالحارسِ نفسِه
    good, msg = imgguard.verdict(dst)
    if not good:
        os.remove(dst)
        print(msg, file=sys.stderr)
        print(f"الناتجُ متجاوزٌ فعلاً — حُذف: {dst}", file=sys.stderr)
        return 2

    print(f"  -> {dst} ({out_w}x{out_h}, {os.path.getsize(dst) // 1024} ك.ب)")
    return 0


def selftest():
    fails = []

    def ok(cond, label):
        print(("  PASS  " if cond else "  FAIL  ") + label)
        if not cond:
            fails.append(label)

    tmp = os.path.join(os.path.dirname(HERE), "..", ".tmp")
    tmp = os.path.abspath(tmp)
    os.makedirs(tmp, exist_ok=True)

    # صورةُ اختبارٍ: نصفٌ أسودُ ونصفٌ أبيضُ، فالقصُّ يُتحقَّق بالقيمةِ
    base = os.path.join(tmp, "crop-src.png")
    W = H = 40
    px = bytearray(W * H * 3)
    for yy in range(H):
        for xx in range(W):
            v = 255 if xx >= 20 else 0
            p = (yy * W + xx) * 3
            px[p] = px[p + 1] = px[p + 2] = v
    imgdown.encode_png(base, px, W, H, 3)

    # 1) القصُّ يأخذ المنطقةَ المطلوبةَ فعلاً — لا منطقةً مجاورة
    a = os.path.join(tmp, "crop-black.png")
    ok(crop(base, a, 0, 0, 10, 10) == 0, "قصُّ الربعِ الأيسرِ ينجح")
    p1, w1, h1, _ = imgdown.decode_png(a)
    ok((w1, h1) == (10, 10), f"أبعادُ القصّةِ 10x10 (كانت {w1}x{h1})")
    ok(max(p1) == 0, "القصّةُ من النصفِ الأسودِ كلُّها سوداء")

    b = os.path.join(tmp, "crop-white.png")
    crop(base, b, 25, 0, 10, 10)
    p2, _, _, _ = imgdown.decode_png(b)
    ok(min(p2) == 255, "القصّةُ من النصفِ الأبيضِ كلُّها بيضاء")

    # 2) التكبيرُ يُضاعف الأبعادَ ويحفظ القيم
    c = os.path.join(tmp, "crop-zoom.png")
    crop(base, c, 0, 0, 10, 10, zoom=3)
    p3, w3, h3, _ = imgdown.decode_png(c)
    ok((w3, h3) == (30, 30), f"التكبيرُ 3x يُنتج 30x30 (كان {w3}x{h3})")
    ok(max(p3) == 0, "التكبيرُ لا يُغيّر القيم")

    # 3) الحدُّ يُفرَض على **الناتجِ بعد التكبير** لا على المصدر
    #    (وهذا بعينه ما يُسقِط الجلسةَ: مصدرٌ سليمٌ وناتجٌ متجاوز)
    big = os.path.join(tmp, "crop-toobig.png")
    ok(crop(base, big, 0, 0, 40, 40, zoom=51) == 2,
       "40x40 بتكبيرِ 51 = 2040 ⇒ يُرفض")
    ok(not os.path.exists(big), "المرفوضُ لا يُكتَب على القرص")
    ok(crop(base, os.path.join(tmp, "crop-edge.png"), 0, 0, 40, 40,
            zoom=50) == 0, "40x40 بتكبيرِ 50 = 2000 بالضبط ⇒ يُقبل")

    # 4) القصُّ خارجَ الإطارِ يُقصَر ولا يُنتج سواداً كاذباً
    d = os.path.join(tmp, "crop-oob.png")
    crop(base, d, 35, 35, 100, 100)
    _, w4, h4, _ = imgdown.decode_png(d)
    ok((w4, h4) == (5, 5), f"القصّةُ خارجَ الإطارِ تُقصَر إلى 5x5 (كانت {w4}x{h4})")

    print(f"\n{'سقط ' + str(len(fails)) if fails else 'كلُّ فحوصِ القصِّ خضراء'}")
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    a = [v for v in sys.argv[1:] if not v.startswith("--")]
    if len(a) < 6:
        print(__doc__)
        sys.exit(1)
    z = 1
    if "--zoom" in sys.argv:
        z = int(sys.argv[sys.argv.index("--zoom") + 1])
    sys.exit(crop(a[0], a[1], a[2], a[3], a[4], a[5], z))
