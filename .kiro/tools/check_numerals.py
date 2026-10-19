#!/usr/bin/env python3
"""حارس: لا أرقام بالرسم الهندي/الفارسي في أي ملفّ من ملفّات المشروع.

قرار المالك الصريح: «والرسوم الهندية انا لا اريدها ابدا في مشاريعي».
الأرقام تُكتب بالرسم العربي الغربي 0123456789 في كل مكان — النصّ والواجهة
والتعليقات وأسماء الملفّات.

ملاحظة على تصميم الحارس: الأحرف الممنوعة **تُبنى من رموزها** (chr) ولا تُكتب
حرفيّاً في هذا الملفّ. النسخة الأولى كتبتها حرفيّاً فسقط الحارس على نفسه
وأبلغ 21 عطلاً كلّها سطرا تعريفه — وحارسٌ يقرأ شرحَه هو كأنّه كود يُعطَّل
بعد أول مرّة، أو أسوأ: يُضاف له استثناءٌ بالاسم فيصير أعمى عن ملفّه.

الاستخدام:
    python3 .kiro/tools/check_numerals.py             # يفحص المشروع كلّه
    python3 .kiro/tools/check_numerals.py <path> ...  # يفحص مسارات بعينها
    python3 .kiro/tools/check_numerals.py --selftest  # يفحص الحارس نفسه

رمز الخروج: 0 نظيف · 2 وُجدت أرقام ممنوعة · 1 خطأ في الحارس أو الاستخدام
"""
import os
import sys

# U+0660..U+0669 أرقام عربيّة-هنديّة · U+06F0..U+06F9 أرقام فارسيّة
EASTERN = tuple(chr(0x0660 + i) for i in range(10))
PERSIAN = tuple(chr(0x06F0 + i) for i in range(10))
BANNED = {}
for _c in EASTERN:
    BANNED[_c] = "هندي"
for _c in PERSIAN:
    BANNED[_c] = "فارسي"

SCAN_EXT = {".md", ".html", ".htm", ".css", ".js", ".mjs", ".json",
            ".py", ".txt", ".svg", ".webmanifest", ".yml", ".yaml"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}


def scan_text(text):
    """يُعيد قائمة (سطر، عمود، حرف، نوع، نصّ السطر)."""
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for col, ch in enumerate(line, 1):
            kind = BANNED.get(ch)
            if kind:
                hits.append((lineno, col, ch, kind, line))
    return hits


def scan_file(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return scan_text(fh.read())
    except (UnicodeDecodeError, OSError):
        return []


def collect(roots):
    files = []
    for root in roots:
        if os.path.isfile(root):
            files.append(root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if os.path.splitext(name)[1].lower() in SCAN_EXT:
                    files.append(os.path.join(dirpath, name))
    return sorted(set(files))


def selftest():
    """يتأكّد أن الحارس يُفرّق فعلاً — فتأكيدٌ لا يُفرّق لا يُثبت شيئاً."""
    cases = [
        ("نصّ بأرقام غربيّة: 150 ريالاً", 0, "السليم يمرّ"),
        ("نصّ برقم هندي: " + chr(0x0662) + "50", 1, "الهندي يُمسَك"),
        ("نصّ برقم فارسي: " + chr(0x06F7), 1, "الفارسي يُمسَك"),
        ("بلا أرقام إطلاقاً", 0, "الخالي يمرّ"),
        ("مختلط 10 و" + chr(0x0660) + chr(0x0661), 2, "يُعَدّ كل موضع"),
        (__doc__, 0, "ملفّ الحارس نفسه نظيف (لا يسقط على شرحه)"),
    ]
    ok = True
    for text, expected, label in cases:
        got = len(scan_text(text))
        mark = "PASS" if got == expected else "FAIL"
        if got != expected:
            ok = False
        print(f"  [{mark}] {label} — متوقَّع {expected} وجاء {got}")

    # الحارس يجب أن يمرّ على ملفّه هو
    own = scan_file(os.path.abspath(__file__))
    mark = "PASS" if not own else "FAIL"
    if own:
        ok = False
    print(f"  [{mark}] الحارس على ملفّه: {len(own)} مطابقة (متوقَّع 0)")
    return 0 if ok else 2


def main(argv):
    args = argv[1:]
    if args and args[0] == "--selftest":
        print("فحوص الحارس الذاتيّة:")
        return selftest()

    roots = args or ["."]
    files = collect(roots)

    # محاسبة كاملة: حارسٌ يفحص صفر ملفّات يقول «نظيف» دائماً وهو أخطر من غيابه.
    if not files:
        print("خطأ في الحارس لا في المشروع: لم يُفحَص أي ملفّ.", file=sys.stderr)
        print(f"المسارات المطلوبة: {roots}", file=sys.stderr)
        return 1

    bad = 0
    # أسماء الملفّات نفسها تُفحَص — مسار فيه رقم هندي ينكسر في URL
    for path in files:
        for ch in os.path.basename(path):
            kind = BANNED.get(ch)
            if kind:
                print(f"BLOCK اسم ملفّ فيه رقم {kind} ({ch}): {path}", file=sys.stderr)
                bad += 1
                break

    for path in files:
        for lineno, col, ch, kind, text in scan_file(path):
            print(f"BLOCK {path}:{lineno}:{col} — رقم {kind} «{ch}»", file=sys.stderr)
            print(f"      {text.strip()[:110]}", file=sys.stderr)
            bad += 1

    if bad:
        print(file=sys.stderr)
        print(f"سقط الحارس: {bad} موضعاً فيه أرقام بالرسم الهندي/الفارسي، "
              f"من أصل {len(files)} ملفّاً مفحوصاً.", file=sys.stderr)
        print("القاعدة: الأرقام تُكتب 0123456789 — قرار صريح من المالك.",
              file=sys.stderr)
        return 2

    print(f"نظيف: {len(files)} ملفّاً مفحوصاً، صفر أرقام هنديّة أو فارسيّة.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
