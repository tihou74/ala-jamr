#!/usr/bin/env python3
"""عدُّ صفحاتِ PDF — بطريقتَين مستقلّتَين يجب أن تتّفقا.

لماذا طريقتان: أوّلُ عدٍّ كتبتُه أخذ **أوّلَ** مطابقةٍ لـ`/Count` فقرأ 8
والملفُّ 12 صفحة. وشجرةُ صفحاتِ PDF فيها عُقَدٌ فرعيّةٌ لكلٍّ منها `/Count`
خاصّ (8 و4 هنا)، والمطابقةُ تبدأ من أقصى اليسارِ فتُصيب الفرعَ لا الجذر.
فالعدُّ على `/Type /Page` و`/MediaBox` — وكلٌّ منهما لكلِّ صفحةٍ مرّةً
واحدة — واختلافُهما يُسقِط التشغيلَ بدل أن يُخمَّن.

الاستخدام: python3 .kiro/tools/pdfpages.py <file.pdf> [أدنى عدد]
"""
import re
import sys


def count(path):
    with open(path, "rb") as fh:
        d = fh.read()
    by_type = len(re.findall(rb"/Type\s*/Page(?![s])", d))
    by_box = len(re.findall(rb"/MediaBox", d))
    counts = [int(x) for x in re.findall(rb"/Count\s+(\d+)", d)]
    return by_type, by_box, counts, len(d), \
        len(re.findall(rb"/Subtype\s*/Image", d)), d.count(b"/FontFile")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    path = argv[1]
    need = int(argv[2]) if len(argv) > 2 else 0
    by_type, by_box, counts, size, imgs, fonts = count(path)

    print(f"  /Type /Page : {by_type}")
    print(f"  /MediaBox   : {by_box}")
    print(f"  /Count (كلّها): {counts}  ← لا يُؤخَذ أوّلُها، فهي عُقَدٌ فرعيّة")
    print(f"  حجم         : {size / 1024:.0f} ك.ب")
    print(f"  صورٌ مُدمجة  : {imgs}")
    print(f"  خطوطٌ مُدمجة : {fonts}")

    if by_type != by_box:
        print(f"خطأ في القياس لا في الملفّ: الطريقتان اختلفتا "
              f"({by_type} ≠ {by_box}).", file=sys.stderr)
        return 1

    pages = by_type
    print(f"  => الصفحات: {pages}")

    if fonts == 0:
        print("  ⚠ صفرُ خطوطٍ مُدمجة: النصُّ لن يُرسَم. هذا متوقَّعٌ في صندوقٍ "
              "بلا خطوطٍ عربيّة — يُطبَع الملفُّ من متصفّحِ المالك.")

    if need and pages < need:
        print(f"سقط: {pages} صفحةً أقلُّ من المطلوب {need}.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
