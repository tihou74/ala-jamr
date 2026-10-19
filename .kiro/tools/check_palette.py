#!/usr/bin/env python3
"""حارس اللوحة: لا لونَ في هذا المشروعِ إلّا من لوحةِ المالك.

اللوحةُ أرسلها المالكُ في 19 أكتوبر 2026، خمسةُ ألوانٍ لا أكثر:
    Emerald Green  #154230
    Deep Burgundy  #5D1E21
    Charcoal Black #101111
    Antique Gold   #A6824A
    Soft Cream     #E6E2DA

وكلُّ درجةٍ أخرى **تُشتقّ حسابياً** بخلطِ أحدِها مع الأسودِ أو الكريمي
بنسبةٍ من قائمةٍ معلومة. فلا لونَ «يُختار بالعين» ويتسرّب.

القاعدتان المفروضتان:
  1. **خارج `tokens.css`: صفرُ ألوانٍ مكتوبةٍ بالرقم.** كلُّ لونٍ يُقرأ من
     متغيّر. وإلّا تسرّب لونٌ لا يُرى في مكانٍ واحدٍ ولا يَتبع أيَّ تغييرٍ
     في اللوحة. ويُستثنى `#000`/`#fff` فهما لمعانُ الأقنعة (mask) لا لون.
  2. **داخل `tokens.css`: كلُّ لونٍ من المجموعةِ المشتقّة.**

لماذا هذا الحارسُ ضروريٌّ هنا بعينه: النسخةُ الأولى من الموقعِ كانت
بلوحةٍ من عندي (برتقاليٌّ ونحاسيٌّ وزعفران)، وبلغ ما لا ينتمي للوحةِ
المالكِ **123 موضعاً** في خمسةِ ملفّات — 108 منها في رسمَين متجهيَّين.
وبلا حارسٍ يعودُ ذلك أوّلَ ما يُضاف قسمٌ جديد.

الاستخدام:
    python3 .kiro/tools/check_palette.py
    python3 .kiro/tools/check_palette.py --selftest
    python3 .kiro/tools/check_palette.py --list      # يطبع المجموعة المسموحة

رمز الخروج: 0 سليم · 2 لونٌ غريب · 1 خطأ في الحارس
"""
import os
import re
import sys

BASE = {
    "emerald": "#154230",
    "burgundy": "#5d1e21",
    "charcoal": "#101111",
    "gold": "#a6824a",
    "cream": "#e6e2da",
}

# النِّسَبُ المستعملةُ فعلاً في tokens.css — تُزاد هنا عند الحاجة بوعي،
# لا تُفتَح على مصراعيها، وإلّا صار الحارسُ يسمح بكلِّ شيء.
MIX_BLACK = [0.16, 0.18, 0.2, 0.34, 0.4, 0.42, 0.45]
MIX_CREAM = [0.05, 0.09, 0.14, 0.15, 0.16, 0.2, 0.3, 0.34, 0.45, 0.62]
MIX_CHARCOAL = [0.1, 0.22, 0.42]      # من الكريمي نحو الفحم

UTILITY = {"#000", "#000000", "#fff", "#ffffff"}

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _hx(c):
    c = c.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _hex(t):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in t)


def _mix(a, b, t):
    A, B = _hx(a), _hx(b)
    return _hex(tuple(A[i] + (B[i] - A[i]) * t for i in range(3)))


def allowed_set():
    out = set(v.lower() for v in BASE.values())
    for name, base in BASE.items():
        for t in MIX_BLACK:
            out.add(_mix(base, "#000000", t))
        for t in MIX_CREAM:
            out.add(_mix(base, BASE["cream"], t))
    for t in MIX_CHARCOAL:
        out.add(_mix(BASE["cream"], BASE["charcoal"], t))
    return out


def strip_comments(text, kind):
    """تُحذف التعليقاتُ أوّلاً: حارسٌ يقرأ شرحَه هو كأنّه كودٌ يُبارك العطل.
    وهذا وقع فعلاً مرّتين في هذا المشروع."""
    before = len(text)
    out = (re.sub(r"/\*.*?\*/", "", text, flags=re.S) if kind == "css"
           else re.sub(r"<!--.*?-->", "", text, flags=re.S))
    return out, before - len(out)


def scan(path):
    kind = "css" if path.endswith(".css") else "html"
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    code, cut = strip_comments(raw, kind)
    hits = []
    for line_no, line in enumerate(code.splitlines(), 1):
        for m in HEX.finditer(line):
            hits.append((line_no, m.group(0), line.strip()[:90]))
    return hits, cut


def targets():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "docs", "__pycache__", ".kiro",
                                    "node_modules", "inbox"}]
        for n in filenames:
            if n.endswith((".css", ".html", ".htm")):
                files.append(os.path.join(dirpath, n))
    return sorted(files)


def selftest():
    import tempfile
    A = allowed_set()
    cases = [
        ("الخمسةُ الأصليّةُ مسموحة", all(v.lower() in A for v in BASE.values()), True),
        ("لونٌ مُشتقٌّ مسموح", _mix(BASE["charcoal"], "#000000", 0.45) in A, True),
        ("البرتقاليُّ القديمُ ممنوع", "#c2410c" in A, False),
        ("النحاسيُّ القديمُ ممنوع", "#b08d57" in A, False),
        ("العاجيُّ القديمُ ممنوع", "#f3ede3" in A, False),
        ("#000 ليس في اللوحةِ بل في المرافق", "#000000" in A, False),
    ]
    ok = True
    for label, got, want in cases:
        mark = "PASS" if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"  [{mark}] {label}")

    # لونٌ غريبٌ في ملفٍّ غيرِ tokens يجب أن يُمسَك
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.css")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(".a{color:#ff00ff}\n/* شرحٌ فيه #123456 لا يُقرأ */\n")
        hits, cut = scan(p)
        caught = [h for h in hits if h[1].lower() not in UTILITY]
        mark = "PASS" if len(caught) == 1 and cut > 0 else "FAIL"
        if mark == "FAIL":
            ok = False
        print(f"  [{mark}] لونٌ غريبٌ يُمسَك والتعليقُ لا يُقرأ "
              f"(أُمسك {len(caught)} · حُذف {cut} حرفَ تعليق)")
    return 0 if ok else 2


def main(argv):
    A = allowed_set()

    if "--list" in argv:
        print(f"المجموعةُ المسموحة ({len(A)} لوناً):")
        for c in sorted(A):
            tag = next((k for k, v in BASE.items() if v.lower() == c), "مُشتقّ")
            print(f"  {c}  {tag}")
        return 0

    if "--selftest" in argv:
        print("فحوصُ حارسِ اللوحةِ الذاتيّة:")
        return selftest()

    files = targets()
    if not files:
        print("خطأ في الحارس لا في المشروع: صفرُ ملفّاتٍ للفحص.",
              file=sys.stderr)
        return 1

    errors = []
    counted = 0
    for path in files:
        rel = os.path.relpath(path, ROOT)
        is_tokens = os.path.basename(path) == "tokens.css"
        hits, cut = scan(path)
        for line_no, color, text in hits:
            counted += 1
            c = color.lower()
            if c in UTILITY:
                continue
            if is_tokens:
                if c not in A:
                    errors.append(
                        f"{rel}:{line_no} — «{color}» ليس من لوحةِ المالكِ "
                        f"ولا مُشتقّاً منها بنسبةٍ معلومة\n      {text}")
            elif "theme-color" in text:
                # استثناءٌ ضيّقٌ واحد: <meta name="theme-color"> لا يقبل
                # متغيّرَ CSS إطلاقاً — فيُسمح بالرقم **بشرطِ** أن يكون من
                # اللوحة. لا إعفاءٌ مفتوحٌ بالاسم: الشرطُ يبقى قائماً.
                if c not in A:
                    errors.append(
                        f"{rel}:{line_no} — theme-color بلونٍ ليس من "
                        f"اللوحة: «{color}»")
            else:
                errors.append(
                    f"{rel}:{line_no} — لونٌ مكتوبٌ بالرقم خارج tokens.css: "
                    f"«{color}»\n      {text}\n      "
                    f"القاعدة: كلُّ لونٍ يُقرأ من متغيّر، فلا يتسرّب لونٌ "
                    f"لا يَتبع تغييرَ اللوحة.")

    print(f"فُحِص {len(files)} ملفّاً · {counted} لوناً مكتوباً بالرقم · "
          f"المجموعةُ المسموحة {len(A)} لوناً")

    if errors:
        print(file=sys.stderr)
        for e in errors:
            print("BLOCK " + e, file=sys.stderr)
        print(f"\nسقط الحارس: {len(errors)} لوناً لا ينتمي للوحةِ المالك.",
              file=sys.stderr)
        return 2

    print("سليم: كلُّ لونٍ من لوحةِ المالكِ أو مُشتقٌّ منها.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
