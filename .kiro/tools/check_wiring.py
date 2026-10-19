#!/usr/bin/env python3
"""حارس الوصلة: كل مرجعٍ في الصفحة يجب أن يُصيب هدفاً موجوداً.

لماذا: في مشروعٍ سابقٍ فيه 33 مجموعةَ اختبارٍ وأكثرُ من 2000 تأكيد — كلُّها
على الحسابِ والمال — ظلَّ زرُّ تصديرٍ ميّتاً شهوراً لأنّ `onclick` كان ينادي
دالّةً لا وجودَ لها في المشروعِ إطلاقاً. والاختباراتُ تحرس **الحساب**، وهذا
يحرس **الوصلة**. وأيقونةُ `<use href="#x">` بلا `<symbol id="x">` تُرسَم
فراغاً صامتاً: لا رسالةَ خطأٍ، ولا أثرَ في وحدةِ التحكّم يراه المستخدم.

ما يُفحَص:
  1. كل أصلٍ محلّيٍّ في href/src موجودٌ على القرص (بعد تجريد ?v=N)
  2. كل `<use href="#id">` له `<symbol id="id">` في نفس الملفّ
  3. كل `href="#anchor"` له `id="anchor"` في نفس الملفّ
  4. كل معالِجِ حدثٍ في الوسم (onclick/onchange/...) ينادي اسماً معرَّفاً
  5. **محاسبة كاملة**: إن لم يساوِ عددُ ما حُلِّل عددَ ما وُجد، يسقط
     التشغيلُ ويقول إنّ الفجوةَ في الحارسِ لا في الكود

الاستخدام:
    python3 .kiro/tools/check_wiring.py [<ملفّ html> ...]
    python3 .kiro/tools/check_wiring.py --selftest

رمز الخروج: 0 سليم · 2 وُجد مرجعٌ معطوب · 1 خطأ في الحارس
"""
import os
import re
import sys

# ------------------------------- أنماط -------------------------------
# نمطٌ شاملٌ للمحاسبة: كل سمة href أو src بأي قيمة
RE_ANY_LINK = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']*)["\']', re.I)
RE_USE = re.compile(r'<use\b[^>]*?(?:href|xlink:href)\s*=\s*["\']([^"\']*)["\']', re.I)
RE_SYMBOL_ID = re.compile(r'<symbol\b[^>]*?\bid\s*=\s*["\']([^"\']+)["\']', re.I)
RE_ANY_ID = re.compile(r'\bid\s*=\s*["\']([^"\']+)["\']')
RE_HANDLER = re.compile(
    r'\bon(?:click|change|input|submit|keyup|keydown|focus|blur)\s*=\s*["\']([^"\']*)["\']',
    re.I,
)
# نداءُ دالّة. النداءُ المسبوقُ بنقطةٍ ليس اسماً عالمياً:
# `load(x).then(go)` تُقرأ خطأً أنّ `then` دالّتُنا.
RE_CALL = re.compile(r'(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(')
RE_COMMENT_HTML = re.compile(r'<!--.*?-->', re.S)


def strip_query(path):
    """يُجرّد ?v=N و#hash — رقمُ الإصدار ليس جزءاً من اسمِ الملفّ."""
    return path.split('?', 1)[0].split('#', 1)[0]


def is_local(url):
    """أصلٌ محلّيٌّ يُفحَص وجودُه. ما ليس محلّياً يُعَدّ ويُستثنى صريحاً."""
    u = url.strip()
    if not u:
        return False
    low = u.lower()
    for prefix in ('http://', 'https://', '//', 'data:', 'mailto:', 'tel:',
                   'javascript:', 'blob:'):
        if low.startswith(prefix):
            return False
    if u.startswith('#'):
        return False
    return True


def defined_names(js_text, html_text):
    """كل أشكال التعريف السبعة لاسمٍ قابلٍ للنداء من الوسم."""
    names = set()
    blob = js_text + "\n" + html_text
    patterns = [
        r'window\.([A-Za-z_$][\w$]*)\s*=',
        r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\(',
        r'\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function|\()',
        r'\blet\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function|\()',
        r'\bvar\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function|\()',
        r'\bclass\s+([A-Za-z_$][\w$]*)',
        r'\basync\s+function\s+([A-Za-z_$][\w$]*)\s*\(',
    ]
    for pat in patterns:
        names.update(re.findall(pat, blob))
    return names


# أسماءٌ مدمجةٌ في المتصفّح يجوز نداؤها من الوسم
BUILTIN_CALLS = {
    'alert', 'confirm', 'prompt', 'open', 'print', 'scrollTo', 'setTimeout',
    'setInterval', 'requestAnimationFrame', 'fetch', 'Number', 'String',
    'parseInt', 'parseFloat', 'encodeURIComponent', 'decodeURIComponent',
    'JSON', 'Boolean', 'Array', 'Object', 'Date', 'Math', 'return', 'if',
    'typeof', 'void',
}


def check_html(path):
    """يُعيد (قائمة أخطاء، إحصاء)."""
    errors = []
    with open(path, encoding='utf-8') as fh:
        raw = fh.read()

    # تُحذف التعليقاتُ أوّلاً: حارسٌ يقرأ شرحَه هو كأنّه كودٌ يُبارك العطل.
    text = RE_COMMENT_HTML.sub('', raw)
    if len(text) > len(raw):
        errors.append(f"{path}: خطأ في الحارس — حذفُ التعليقات أطال النصّ")
    if not text.strip():
        errors.append(f"{path}: خطأ في الحارس — حذفُ التعليقات أفرغ النصّ")

    base = os.path.dirname(os.path.abspath(path))
    stats = {'links': 0, 'local': 0, 'external': 0, 'anchors': 0,
             'uses': 0, 'handlers': 0, 'calls': 0}

    # ---------- 1 + 3: الروابط ----------
    # تُستثنى سماتُ href داخل <use> لأنّها مراجعُ رموزٍ لا مراسي صفحة،
    # ولها فحصُها الخاصّ أدناه. بلا هذا الاستثناء يُبلَّغ العطلُ الواحد
    # مرّتين بوصفين مختلفين، فيُقرأ عطلانِ ويُضيَّع وقتٌ في مطاردةِ ثانٍ
    # لا وجودَ له.
    use_tags = re.findall(r'<use\b[^>]*>', text, re.I)
    use_hrefs = []
    for tag in use_tags:
        use_hrefs.extend(RE_ANY_LINK.findall(tag))

    all_links_raw = RE_ANY_LINK.findall(text)
    all_links = list(all_links_raw)
    for h in use_hrefs:
        if h in all_links:
            all_links.remove(h)

    stats['links'] = len(all_links)
    ids = set(RE_ANY_ID.findall(text))

    classified = 0
    for url in all_links:
        u = url.strip()
        if u.startswith('#'):
            classified += 1
            stats['anchors'] += 1
            anchor = u[1:]
            if anchor and anchor not in ids:
                errors.append(
                    f"{path}: مِرساةٌ معطوبة href=\"{u}\" — لا عنصرَ بـ id=\"{anchor}\"")
        elif is_local(u):
            classified += 1
            stats['local'] += 1
            target = os.path.join(base, strip_query(u))
            if not os.path.isfile(target):
                errors.append(
                    f"{path}: أصلٌ مفقود href/src=\"{u}\" — لا ملفَّ عند {target}")
        else:
            classified += 1
            stats['external'] += 1

    # محاسبة كاملة
    if classified != stats['links']:
        errors.append(
            f"{path}: خطأ في الحارس — وُجد {stats['links']} رابطاً "
            f"وحُلِّل {classified}. الفجوةُ في الحارسِ لا في الكود.")

    # ---------- 2: رموز SVG ----------
    # يُقبَل أن يُشير <use> إلى **أي** عنصرٍ بمعرِّف، لا إلى <symbol> وحده:
    # فـ<defs><path id="x"/></defs> ثم <use href="#x"> صحيحٌ تماماً في SVG،
    # وحصرُ الفحصِ على <symbol> كان يُسقط رسوماً سليمةً — وحارسٌ يمنع أكثرَ
    # من اللازم يُعطَّل بعد حين فيَضيع نفعُه كلُّه.
    symbols = set(RE_SYMBOL_ID.findall(text)) | ids
    uses = RE_USE.findall(text)
    stats['uses'] = len(uses)
    for u in uses:
        u = u.strip()
        if not u.startswith('#'):
            # مرجعٌ خارجيّ: <use href="file.svg#id"> غيرُ موثوقٍ في المتصفّحات
            errors.append(
                f"{path}: <use href=\"{u}\"> مرجعٌ خارجيّ — "
                f"المتصفّحاتُ لا تُعوّل عليه، أدرِج الرمزَ في الصفحة")
            continue
        sid = u[1:]
        if sid not in symbols:
            errors.append(
                f"{path}: أيقونةٌ ميّتة <use href=\"{u}\"> — "
                f"لا عنصرَ بـ id=\"{sid}\" في الملفّ (تُرسَم فراغاً صامتاً)")

    # ---------- 4: معالِجاتُ الأحداث في الوسم ----------
    js_text = ''
    for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', text, re.S | re.I):
        js_text += '\n' + m.group(1)
    # وملفّات السكربت المحلّيّة
    for url in all_links:
        u = strip_query(url.strip())
        if is_local(u) and u.endswith('.js'):
            p = os.path.join(base, u)
            if os.path.isfile(p):
                with open(p, encoding='utf-8') as fh:
                    js_text += '\n' + fh.read()

    known = defined_names(js_text, text) | BUILTIN_CALLS
    handlers = RE_HANDLER.findall(text)
    stats['handlers'] = len(handlers)
    for body in handlers:
        for name in RE_CALL.findall(body):
            stats['calls'] += 1
            if name not in known:
                errors.append(
                    f"{path}: معالِجٌ ميّت — ينادي \"{name}()\" وهي غيرُ معرَّفةٍ "
                    f"في أي سكربت (زرٌّ بلا دالّةٍ لا يُعطي رسالةً للمستخدم)")

    return errors, stats


# ------------------------------- فحوصٌ ذاتيّة -------------------------------

SELFTEST_CASES = [
    # (وصف، html، عددُ الأخطاءِ المتوقَّع)
    ("أيقونة سليمة",
     '<svg><symbol id="a"></symbol></svg><svg><use href="#a"/></svg>', 0),
    ("أيقونة ميّتة",
     '<svg><symbol id="a"></symbol></svg><svg><use href="#b"/></svg>', 1),
    ("مِرساة سليمة", '<div id="go"></div><a href="#go">x</a>', 0),
    ("مِرساة معطوبة", '<div id="go"></div><a href="#nope">x</a>', 1),
    ("معالِجٌ سليم",
     '<script>function doIt(){}</script><button onclick="doIt()">x</button>', 0),
    ("معالِجٌ ميّت",
     '<script>function doIt(){}</script><button onclick="missing()">x</button>', 1),
    ("window.x = سليم",
     '<script>window.go = function(){}</script><button onclick="go()">x</button>', 0),
    ("const x = () سليم",
     '<script>const go = () => {}</script><button onclick="go()">x</button>', 0),
    ("النداءُ المسبوقُ بنقطةٍ لا يُحسَب اسماً عالمياً",
     '<script>function load(){}</script><button onclick="load().then(z)">x</button>', 0),
    ("رابطٌ خارجيٌّ لا يُفحَص وجودُه",
     '<a href="https://example.com/x.css">x</a>', 0),
    ("التعليقُ لا يُقرأ كودَاً",
     '<!-- <use href="#ghost"/> --><svg><symbol id="a"></symbol></svg>', 0),
    ("مرجعُ <use> الخارجيُّ يُرفَض",
     '<svg><use href="icons.svg#a"/></svg>', 1),
]


def selftest():
    import tempfile
    ok = True
    for label, html, expected in SELFTEST_CASES:
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'page.html')
            with open(p, 'w', encoding='utf-8') as fh:
                fh.write(html)
            errs, _ = check_html(p)
        got = len(errs)
        mark = 'PASS' if got == expected else 'FAIL'
        if got != expected:
            ok = False
        print(f"  [{mark}] {label} — متوقَّع {expected} وجاء {got}")
        if got != expected:
            for e in errs:
                print(f"         {e}")
    return 0 if ok else 2


def main(argv):
    args = argv[1:]
    if args and args[0] == '--selftest':
        print("فحوصُ حارسِ الوصلةِ الذاتيّة:")
        return selftest()

    if args:
        files = args
    else:
        files = []
        for dirpath, dirnames, filenames in os.walk('.'):
            dirnames[:] = [x for x in dirnames
                           if x not in {'.git', 'node_modules', '__pycache__'}]
            for name in filenames:
                if name.lower().endswith(('.html', '.htm')):
                    files.append(os.path.join(dirpath, name))

    if not files:
        print("خطأ في الحارس لا في المشروع: لم يُفحَص أي ملفّ HTML.",
              file=sys.stderr)
        return 1

    all_errors = []
    total = {'links': 0, 'local': 0, 'external': 0, 'anchors': 0,
             'uses': 0, 'handlers': 0, 'calls': 0}
    for path in sorted(files):
        errs, st = check_html(path)
        all_errors.extend(errs)
        for k in total:
            total[k] += st.get(k, 0)

    print(f"فُحِص {len(files)} ملفّاً: "
          f"{total['links']} رابطاً ({total['local']} محلّي · "
          f"{total['external']} خارجي · {total['anchors']} مِرساة) · "
          f"{total['uses']} أيقونة · {total['handlers']} معالِجاً "
          f"({total['calls']} نداءً)")

    # حارسٌ يفحص صفرَ أهدافٍ يقول «سليم» دائماً
    if total['links'] == 0 and total['uses'] == 0:
        print("خطأ في الحارس: صفرُ أهدافٍ — لم يُفحَص شيءٌ فعلاً.",
              file=sys.stderr)
        return 1

    if all_errors:
        print(file=sys.stderr)
        for e in all_errors:
            print("BLOCK " + e, file=sys.stderr)
        print(f"\nسقط الحارس: {len(all_errors)} مرجعاً معطوباً.", file=sys.stderr)
        return 2

    print("سليم: كل مرجعٍ يُصيب هدفاً موجوداً.")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
