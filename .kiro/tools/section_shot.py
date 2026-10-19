#!/usr/bin/env python3
"""لقطةُ قسمٍ بعينه — والدليلُ على أنّه هو **داخلَ الصورة**.

لماذا هذه الأداة: لقطةُ `index.html#fire` **لا تُظهر قسمَ الجمر**.
`scroll-behavior: smooth` في `base.css` يجعل نقلةَ المِرساةِ حركةً،
والساعةُ الوهميّةُ (`--virtual-time-budget`) تنقطع بعد نحوِ 15 بكسلاً —
فتخرج ثمانيةُ ملفّاتٍ **كلُّها الواجهةُ** بفروقٍ تُضلّل: المقاساتُ
مختلفةٌ وبصمةُ md5 مختلفةٌ، فيُقرأ الاختلافُ «أقسامٌ مختلفة». وأنا
قرأتُه كذلك، ولم ينكشف إلّا بالنظرِ في صورتين.

فالعلاجُ ليس «أضفْ تأخيراً»، بل **أن تحمل الصورةُ دليلَها**: شريطٌ
مُحقَنٌ في النسخةِ المؤقّتةِ يطبع على الصورةِ اسمَ القسمِ المطلوبِ،
وموضعَ التمريرِ، و**بُعدَ أعلى القسمِ عن أعلى النافذة** — فإن لم يكن
صفراً تقريباً فاللقطةُ ليست لهذا القسمِ ولو بدت معقولة.

وشرطان إلزاميّان:
  · المعرّفُ يجب أن يكون موجوداً في `index.html` — فمعرّفٌ مكتوبٌ
    خطأً يُنتج لقطةَ الواجهةِ بلا أيِّ شكوى، وهذا بعينه ما حدث
  · الحدُّ (2000 بكسل) **لا يُعاد تنفيذُه هنا**: تُنادى `shoot.shoot`
    فيبقى المَخنَقُ واحداً. وأداةٌ جديدةٌ تكتب حدَّها بنفسِها هي
    الطريقُ الذي يتسلّل منه التجاوز

النسخةُ المؤقّتةُ تُكتب في **جذرِ المستودع** لا في مجلّدٍ آخر، لأنّ
`assets/...` مساراتٌ نسبيّة: نسخةٌ في مجلّدٍ أعمقَ تفقد كلَّ أصلٍ
وتُصوَّر صفحةً عاريةً تبدو «تصميماً سيّئاً».

الاستخدام:
    python3 .kiro/tools/section_shot.py <معرّف> <out.png> [عرض] [ارتفاع]
    python3 .kiro/tools/section_shot.py --selftest
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import shoot  # noqa: E402  — المَخنَقُ الوحيدُ للحدّ

PAGE = os.path.join(ROOT, "index.html")
HEADER_SEL = "header.nav"

# الشريطُ لاتينيُّ الأرقامِ بقصد: حارسُ الأرقامِ يمنع الرسمَ الهنديَّ
# والفارسيَّ في كلِّ ملفّ، وهذا الملفُّ ليس مستثنى.
RIG = """
<style id="shot-rig">
  /* ---- 1. العزلُ بدلَ التمرير ----
     القيدُ المقيس: `--screenshot` في chrome-headless-shell **لا يُصوّر
     نافذةً مُمرَّرة**. جُرّب التمريرُ الفوريُّ إلى y=1738 والشريطُ
     يُثبت بـ--dump-dom أنّ الموضعَ صحيحٌ تماماً
     (`section-top-offset=0px OK`) **والصورةُ خرجت فحماً أسودَ صافياً**
     بـ5290 بايتاً بالضبط في ثماني محاولات. فالخللُ في التصويرِ لا في
     التمرير. ولهذا لا يُمرَّر إطلاقاً: يُخفى كلُّ شقيقٍ للقسمِ فيصير
     القسمُ المطلوبُ **أعلى المستند**، فتُصوَّر نافذةٌ غيرُ مُمرَّرة.
     (وهذا أيضاً يتجنّب الإطارَ `iframe` الذي مَنعَته سياسةُ الأصولِ
     في `file://` فعطّلت أداةَ المحاولةِ السابقة.) */
  main > *:not(#__SID__) { display: none !important; }
  header.nav { display: none !important; }

  /* ---- 2. الكشفُ يُفرَض ----
     `html.js [data-reveal]` تبدأ `opacity:0` ولا يُظهرها إلّا المراقبُ
     عند التمرير. وبلا هذا الفرضِ تخرج اللقطةُ سوداءَ ويُقرأ السوادُ
     «تصميماً فاشلاً» وهو محتوًى شفّافٌ لم يُكشَف. ويطبع الشريطُ
     `reveal=forced` فلا تُقرأ اللقطةُ يوماً شهادةً على أنّ الكشفَ يعمل. */
  html.js [data-reveal] {
    opacity: 1 !important;
    transform: none !important;
    transition: none !important;
  }

  #shot-badge {
    position: fixed; bottom: 0; left: 0; z-index: 99999;
    background: #000; color: #0f0; border-top: 1px solid #0f0;
    border-right: 1px solid #0f0; padding: 3px 9px;
    font: 12px/1.5 monospace; direction: ltr; white-space: pre;
  }
</style>
<script>
/* لا مؤقّتَ هنا بقصد: نسخةٌ أولى بـ`setTimeout(700)` داخلَ `load` لم
   تطبع الشريطَ إطلاقاً — فما بعد المؤقّتِ لا يُنفَّذ تحت
   `--virtual-time-budget`. فالقياسُ والطبعُ متزامنانِ داخلَ `load`،
   وهو يقع بعد الخطوطِ والصورِ فالتخطيطُ مستقرٌّ عنده. */
window.addEventListener("load", function () {
  var sid = "__SID__";
  var el = document.getElementById(sid);
  var r = el ? el.getBoundingClientRect() : null;
  var y = Math.round(window.pageYOffset);
  var top = r ? Math.round(r.top) : -99999;
  var n = el ? el.querySelectorAll("[data-reveal]").length : 0;
  var b = document.createElement("div");
  b.id = "shot-badge";
  b.textContent =
    "#" + sid + (el ? "" : "  MISSING-SECTION") +
    "  isolated  scrollY=" + y + (y === 0 ? "" : "  SCROLLED-SHOT-IS-BLACK") +
    "  top=" + top + "px" + (Math.abs(top) <= 4 ? "  OK" : "  WRONG-VIEW") +
    "  section-h=" + (r ? Math.round(r.height) : 0) +
    "  reveal=forced(" + n + ")";
  document.body.appendChild(b);
});
</script>
"""


def section_ids(html):
    return set(re.findall(r'id="([A-Za-z0-9_-]+)"', html))


# وضعُ «بلا نصّ»: يُخفي النصَّ ويُبقي الصورةَ والحجابَ كما هما، فيُقاس
# **سطوعُ الخلفيّةِ وحدَها** تحت موضعِ النصّ. ولماذا: قياسُ منطقةٍ فيها
# نصٌّ فاتحٌ يَعُدُّ بكسلاتِ الحروفِ نفسَها خلفيّةً ساطعة، فيخرج «أسوأُ
# موضعٍ» أفضلَ من الوسيطِ — وهو مقلوبٌ ولا معنى له. فيُقاس الوسيطُ على
# ما فيه نصٌّ، ويُقاس الأسوأُ على ما لا نصَّ فيه.
NO_TEXT = """
<style id="shot-notext">
  #__SID__, #__SID__ * {
    color: transparent !important;
    text-shadow: none !important;
    border-color: transparent !important;
  }
</style>
"""


def build_rig(sid, no_text=False):
    rig = RIG.replace("__SID__", sid).replace("__HEADER__", HEADER_SEL)
    if no_text:
        rig += NO_TEXT.replace("__SID__", sid)
    return rig


def inject(html, rig):
    """يُحقَن قبل </head>. لو غاب الوسمُ فلا حقنَ صامت: يُرمى."""
    if "</head>" not in html:
        raise ValueError("لا </head> في index.html — لا يُحقَن بالتخمين")
    return html.replace("</head>", rig + "</head>", 1)


def shot(sid, out, w=1280, h=900, no_text=False):
    with open(PAGE, encoding="utf-8") as f:
        html = f.read()

    ids = section_ids(html)
    if sid not in ids:
        print(f"مرفوض: لا عنصرَ بمعرّف '{sid}' في index.html.", file=sys.stderr)
        print("  وبلا هذا الفحصِ تُنتَج لقطةُ الواجهةِ بلا شكوى.",
              file=sys.stderr)
        print(f"  المعرّفاتُ الموجودة: {', '.join(sorted(ids))}",
              file=sys.stderr)
        return 2

    tmp = os.path.join(ROOT, f".shot-rig-{sid}.html")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(inject(html, build_rig(sid, no_text)))
        # 2500ms: 700 للشريطِ وما بقي لانتقالاتِ الكشف
        return shoot.shoot(tmp, out, w, h, wait_ms=2500)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ---------------------------------------------------------------- فحوصٌ ذاتيّة


def selftest():
    """يُجرَّب على العطلِ الذي وُجدت الأداةُ له، وإلّا فلا يُوثق بها."""
    fails = []

    def ok(cond, label):
        print(("  PASS  " if cond else "  FAIL  ") + label)
        if not cond:
            fails.append(label)

    with open(PAGE, encoding="utf-8") as f:
        html = f.read()

    ids = section_ids(html)
    # 1) العطلُ الأصليّ: الأقسامُ التي أُريد تصويرُها موجودةٌ فعلاً
    for sid in ("story", "fire", "rice", "grill", "table", "majlis", "contact"):
        ok(sid in ids, f"المعرّف '{sid}' موجودٌ في index.html")

    # 2) معرّفٌ مختلَقٌ يُرفض — ولو مرَّ لأُنتجت لقطةُ الواجهة
    ok("no-such-section-xyz" not in ids, "معرّفٌ مختلَقٌ غيرُ موجود")
    rc = shot("no-such-section-xyz", os.path.join(ROOT, ".tmp", "selftest-should-not-exist.png"))
    ok(rc == 2, "المعرّفُ المختلَقُ يُرفض برمزِ 2 قبل تشغيلِ المتصفّح")

    # 3) السببُ الجذريُّ مكتوبٌ في الصفحةِ فعلاً — فلو حُذف لبطلت الحاجة
    base = os.path.join(ROOT, "assets", "base.css")
    with open(base, encoding="utf-8") as f:
        css = f.read()
    # سببُ العطلِ الأوّلِ (المِرساةُ لا تنقل) ما زال قائماً في الصفحة،
    # ويُذكر هنا لأنّه الذي يمنع استعمالَ `index.html#fire` مباشرةً.
    # **ولم يبقَ تأكيدٌ على «الحقنةُ تُبطل الحركة»**: كان مكتوباً وسقط،
    # وسقوطُه صحيحٌ — فالعزلُ لا يُمرِّر أصلاً، فإبطالُ الحركةِ صار
    # بلا معنى. والتأكيدُ على سلوكٍ تُرك عن قصدٍ يُصلَّح لا يُضعَّف.
    ok("scroll-behavior: smooth" in css,
       "scroll-behavior:smooth قائمٌ في base.css (سببُ فشلِ المِرساة)")
    rig = build_rig("fire")
    ok("scroll-behavior" not in rig,
       "الحقنةُ لا تتعرّض لـscroll-behavior: العزلُ لا يُمرِّر إطلاقاً")

    # 4) الحقنُ لا يكون صامتاً
    ok("__SID__" not in rig and 'sid = "fire"' in rig,
       "المعرّفُ يُستبدل في الحقنةِ فعلاً")
    try:
        inject("<html><body>x</body></html>", rig)
        ok(False, "غيابُ </head> يُرمى لا يُتخطّى")
    except ValueError:
        ok(True, "غيابُ </head> يُرمى لا يُتخطّى")
    ok(inject(html, rig).index(rig) < inject(html, rig).index("</head>"),
       "الحقنةُ قبل </head>")

    # 5) الحدُّ لا يُعاد تنفيذُه هنا بل يُنادى مَخنَقُ shoot
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    ok("shoot.shoot(" in src, "يُنادى مَخنَقُ shoot لا حدٌّ محليٌّ جديد")
    ok(shoot.MAX_DIM == 2000, "حدُّ المَخنَقِ 2000 بكسل")
    ok(shot("fire", os.path.join(ROOT, ".tmp", "selftest-should-not-exist.png"), 2400, 900) == 2,
       "عرضٌ 2400 يُرفض عبر المَخنَق")
    ok(shot("fire", os.path.join(ROOT, ".tmp", "selftest-should-not-exist.png"), 1280, 2001) == 2,
       "ارتفاعٌ 2001 يُرفض عبر المَخنَق")

    # 6) الشريطُ يُنبّه نصّاً عند اللقطةِ الخطأ — لا يُكتفى بالرقم
    ok("WRONG-VIEW" in rig and "MISSING-SECTION" in rig,
       "الشريطُ يطبع تنبيهاً صريحاً لا رقماً يُقرأ بالتأويل")
    ok("window.pageYOffset" in rig and "section-top-offset" in rig,
       "الشريطُ يطبع موضعَ التمريرِ وبُعدَ أعلى القسم")

    # 7) العطلانِ اللذانِ وقعا فعلاً — ولو عادا لعادت اللقطةُ السوداء
    # تُحذف التعليقاتُ أوّلاً: هذا التأكيدُ سقط أوّلَ مرّةٍ لأنّه قرأ
    # **شرحَ الحقنةِ عن نفسِها** (تعليقٌ يذكر setTimeout ليقول إنّه مُزال)
    # كأنّه كودٌ عاملٌ. وحارسٌ يقرأ تعليقَه يُدين السليمَ ويُبارك المعطوب.
    bare = re.sub(r"/\*.*?\*/", "", rig, flags=re.S)
    ok(len(bare) < len(rig) and len(bare) > len(rig) // 2,
       "حذفُ التعليقاتِ قصَّر النصَّ ولم يُفرغه")
    ok("setTimeout" not in bare,
       "لا مؤقّتَ في كودِ الحقنة (المؤقّتُ لا يُنفَّذ تحت الساعةِ الوهميّة)")
    ok("opacity: 1 !important" in rig,
       "الكشفُ مفروضٌ بالأنماط (وإلّا خرجت اللقطةُ فحماً أسودَ صافياً)")
    ok("reveal=forced" in rig,
       "الشريطُ يُعلن أنّ الكشفَ مفروضٌ فلا تُقرأ اللقطةُ شهادةً عليه")
    ok("opacity: 0" in css and "[data-reveal]" in css,
       "سببُ السوادِ قائمٌ في base.css: [data-reveal] تبدأ opacity 0")

    # 8) العزلُ لا التمرير — القيدُ الذي أهدر ثماني لقطاتٍ سوداء
    ok("window.scrollTo" not in bare,
       "لا تمريرَ في كودِ الحقنة (النافذةُ المُمرَّرةُ تُصوَّر سوداء)")
    ok("main > *:not(#fire)" in rig,
       "الأشقّاءُ يُخفَون فيصير القسمُ أعلى المستند")
    ok("header.nav { display: none" in rig,
       "الشريطُ العلويُّ يُخفى فلا يحجب أعلى القسم")
    ok("SCROLLED-SHOT-IS-BLACK" in rig,
       "الشريطُ يُنبّه لو وُجد تمريرٌ — فالسوادُ لا يُشخَّص بالنظرِ مرّتين")

    # 9) وضعُ «بلا نصّ» يُطلَب صريحاً ولا يقع افتراضاً: لقطةٌ بلا نصٍّ
    #    تُقرأ حكماً على التصميمِ هي كارثةٌ صامتة
    ok("color: transparent" in build_rig("fire", no_text=True),
       "وضعُ بلا نصٍّ يُخفي النصَّ عند طلبِه")
    ok("color: transparent" not in build_rig("fire"),
       "والوضعُ الافتراضيُّ يُبقي النصَّ — فلا تُخفى الكتابةُ بلا طلب")
    ok("#fire, #fire *" in build_rig("fire", no_text=True),
       "الإخفاءُ محصورٌ في القسمِ المطلوبِ لا الصفحةِ كلّها")

    # 10) النسخةُ المؤقّتةُ في الجذرِ (وإلّا انكسرت مساراتُ assets النسبيّة)
    ok(os.path.dirname(os.path.join(ROOT, ".shot-rig-x.html")) == ROOT,
       "النسخةُ المؤقّتةُ في جذرِ المستودعِ فتبقى assets/ صحيحة")
    leftovers = [p for p in os.listdir(ROOT) if p.startswith(".shot-rig-")]
    ok(not leftovers, f"لا نسخةَ مؤقّتةً متروكةً بعد التشغيل ({leftovers})")

    print(f"\n{'سقط ' + str(len(fails)) if fails else 'كلُّ الفحوصِ الذاتيّةِ خضراء'}")
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    a = [v for v in sys.argv[1:] if not v.startswith("--")]
    sys.exit(shot(a[0], a[1],
                  int(a[2]) if len(a) > 2 else 1280,
                  int(a[3]) if len(a) > 3 else 900,
                  no_text="--no-text" in sys.argv))
