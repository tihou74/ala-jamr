#!/usr/bin/env python3
"""شريطٌ من الصفحةِ كما تُرى متصلةً — بلا تمريرٍ وبلا تجاوزِ الحدّ.

المسألة: المالكُ يريد أن **يرى الموقع**، والأقسامُ المعزولةُ
(`section_shot.py`) تُظهر كلَّ قسمٍ وحدَه بلا شريطٍ علويٍّ ولا ما قبله
ولا ما بعده — فهي للحكمِ على قسمٍ لا لرؤيةِ موقع.

وقيدانِ مقيسانِ يمنعان الطريقَ المعتاد:
  · `--screenshot` **لا يُصوّر نافذةً مُمرَّرة** (تخرج سوداءَ صافية)،
    فلا يُمكن التمريرُ شريطاً شريطاً
  · ولا لقطةَ صفحةٍ كاملة: الصفحةُ نحوُ 8000 بكسلٍ والحدُّ 2000

فالحيلةُ: تُزاح الصفحةُ لأعلى بهامشٍ **سالبٍ** بدلَ التمرير، فيأتي
الشريطُ المطلوبُ داخلَ النافذةِ و**التمريرُ يبقى صفراً** فتُرسَم اللقطةُ.
والشريطُ العلويُّ يبقى ظاهراً كما في الموقعِ الحقيقيّ.

الاستخدام:
    python3 .kiro/tools/page_band.py <out-prefix> [ارتفاعُ الشريط] [العرض]
    python3 .kiro/tools/page_band.py --selftest
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import shoot  # noqa: E402  — المَخنَقُ الوحيدُ للحدّ

PAGE = os.path.join(ROOT, "index.html")
MAX_DIM = shoot.MAX_DIM

RIG = """
<style id="band-rig">
  /* الإزاحةُ بهامشٍ سالبٍ لا بتمرير: النافذةُ المُمرَّرةُ تُصوَّر سوداء */
  main { margin-block-start: -__OFFSET__px !important; }

  /* الكشفُ يُفرَض: [data-reveal] تبدأ opacity 0 ولا يُظهرها إلّا
     المراقبُ عند التمرير، ولا تمريرَ هنا ⇒ شريطٌ أسودُ بلا هذا الفرض */
  html.js [data-reveal] {
    opacity: 1 !important;
    transform: none !important;
    transition: none !important;
  }

  #band-badge {
    position: fixed; bottom: 0; left: 0; z-index: 99999;
    background: #000; color: #0f0; border-top: 1px solid #0f0;
    border-right: 1px solid #0f0; padding: 2px 8px;
    font: 11px/1.4 monospace; direction: ltr; white-space: pre;
  }
</style>
<script>
window.addEventListener("load", function () {
  var off = __OFFSET__;
  var total = Math.round(document.documentElement.scrollHeight) + off;
  var b = document.createElement("div");
  b.id = "band-badge";
  b.textContent =
    "band y=" + off + ".." + (off + window.innerHeight) +
    "  of~" + total +
    "  scrollY=" + Math.round(window.pageYOffset) +
    (Math.round(window.pageYOffset) === 0 ? "" : "  SCROLLED-WILL-BE-BLACK");
  document.body.appendChild(b);
});
</script>
"""


def inject(html, offset):
    if "</head>" not in html:
        raise ValueError("لا </head> في index.html — لا يُحقَن بالتخمين")
    rig = RIG.replace("__OFFSET__", str(int(offset)))
    return html.replace("</head>", rig + "</head>", 1)


def band(out, offset, w=1280, h=1700):
    """شريطٌ واحدٌ عند إزاحةٍ معلومة."""
    with open(PAGE, encoding="utf-8") as f:
        html = f.read()
    tmp = os.path.join(ROOT, f".band-rig-{int(offset)}.html")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(inject(html, offset))
        return shoot.shoot(tmp, out, w, h, wait_ms=2500)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def series(prefix, h=1700, w=1280, total=9000):
    """أشرطةٌ متتابعةٌ تُغطّي الصفحةَ، بتراكبٍ بسيطٍ فلا يُقطَع سطر."""
    overlap = 80
    step = h - overlap
    n = 0
    y = 0
    while y < total:
        out = f"{prefix}-{n + 1:02d}.png"
        print(f"── شريط {n + 1}: y={y}..{y + h}")
        if band(out, y, w, h) != 0:
            return 1
        n += 1
        y += step
        if n > 12:
            break
    print(f"\n{n} شريطاً — بعرضِ {w} وارتفاعِ {h} لكلِّ شريط.")
    return 0


def selftest():
    fails = []

    def ok(cond, label):
        print(("  PASS  " if cond else "  FAIL  ") + label)
        if not cond:
            fails.append(label)

    with open(PAGE, encoding="utf-8") as f:
        html = f.read()

    rig = RIG.replace("__OFFSET__", "1700")
    ok("__OFFSET__" not in rig, "الإزاحةُ تُستبدل فعلاً في الحقنة")
    ok("margin-block-start: -1700px" in rig,
       "الإزاحةُ بهامشٍ سالبٍ بالقيمةِ المطلوبة")
    # تُحذف التعليقاتُ قبل الفحصِ: حارسٌ يقرأ شرحَه هو يُبارك العطل
    bare = re.sub(r"/\*.*?\*/", "", rig, flags=re.S)
    ok(len(bare) < len(rig), "حذفُ التعليقاتِ قصَّر النصَّ")
    ok("scrollTo" not in bare, "لا تمريرَ في كودِ الحقنة")
    ok("opacity: 1 !important" in rig, "الكشفُ مفروضٌ فلا يخرج الشريطُ أسود")
    ok("SCROLLED-WILL-BE-BLACK" in rig, "الشريطُ يُنبّه لو وقع تمريرٌ")

    try:
        inject("<html><body>x</body></html>", 0)
        ok(False, "غيابُ </head> يُرمى لا يُتخطّى")
    except ValueError:
        ok(True, "غيابُ </head> يُرمى لا يُتخطّى")

    # الحدُّ يُفرَض عبرَ المَخنَقِ لا بحدٍّ محليٍّ جديد
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    ok("shoot.shoot(" in src, "يُنادى مَخنَقُ shoot")
    ok(MAX_DIM == 2000, "حدُّ المَخنَقِ 2000 بكسل")
    out = os.path.join(ROOT, ".tmp", "band-should-not-exist.png")
    ok(band(out, 0, 1280, 2001) == 2, "ارتفاعُ شريطٍ 2001 يُرفض")
    ok(band(out, 0, 2400, 900) == 2, "عرضُ 2400 يُرفض")
    ok(not os.path.exists(out), "المرفوضُ لا يُكتَب")

    leftovers = [p for p in os.listdir(ROOT) if p.startswith(".band-rig-")]
    ok(not leftovers, f"لا نسخةَ مؤقّتةً متروكة ({leftovers})")

    print(f"\n{'سقط ' + str(len(fails)) if fails else 'كلُّ فحوصِ الأشرطةِ خضراء'}")
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    a = [v for v in sys.argv[1:] if not v.startswith("--")]
    if not a:
        print(__doc__)
        sys.exit(1)
    sys.exit(series(a[0],
                    int(a[1]) if len(a) > 1 else 1700,
                    int(a[2]) if len(a) > 2 else 1280))
