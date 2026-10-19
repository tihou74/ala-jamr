#!/usr/bin/env bash
# ===========================================================
# عالجمر — تشغيلُ كلِّ الحوارس في أمرٍ واحد
#
# لماذا هذا الملفّ: **سكربتُ فحصٍ موجودٌ في المستودعِ وغيرُ مربوطٍ بشيءٍ
# يُشغّله هو صفرُ تأكيدات.** في مشروعٍ سابقٍ بقي سكربتٌ بـ69 تأكيداً على
# مالِ الدرجِ لم يُشغَّل قطّ، وكان يُطمئنُ من يقرأ قائمةَ الملفّات.
# فكلُّ حارسٍ يُضاف هنا، وأيُّ حارسٍ في .kiro/tools/check_*.py غيرُ مذكورٍ
# في هذا الملفّ يُسقِط التشغيل.
#
# الاستخدام:  bash verify.sh
# ===========================================================
set -uo pipefail
cd "$(dirname "$0")"

pass=0
fail=0

run() {
  local label="$1"; shift
  printf '\n\033[1m── %s\033[0m\n' "$label"
  if "$@"; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    printf '\033[31m   ✗ سقط: %s\033[0m\n' "$label"
  fi
}

echo "═══════════ حوارسُ عالجمر ═══════════"

# الفحوصُ الذاتيّةُ أوّلاً: حارسٌ لم يُجرَّب على عطلٍ معروفٍ لا يُوثق به،
# وحارسٌ يسقط على نفسِه يُعطّل بعد حين.
run "فحوصُ حارسِ الأرقامِ الذاتيّة" \
    python3 .kiro/tools/check_numerals.py --selftest
run "فحوصُ حارسِ الوصلةِ الذاتيّة" \
    python3 .kiro/tools/check_wiring.py --selftest
run "فحوصُ حارسِ اللوحةِ الذاتيّة" \
    python3 .kiro/tools/check_palette.py --selftest

# ثمّ الحوارسُ على المشروع
run "لا أرقامَ بالرسمِ الهنديِّ أو الفارسيّ" \
    python3 .kiro/tools/check_numerals.py
run "كلُّ مرجعٍ يُصيب هدفاً موجوداً" \
    python3 .kiro/tools/check_wiring.py index.html
run "لا لونَ إلّا من لوحةِ المالك" \
    python3 .kiro/tools/check_palette.py
run "لا صورةَ تتجاوز 2000 بكسل" \
    bash -c 'python3 .kiro/tools/imgguard.py check docs/preview/*.png'

# محاسبةُ الحوارسِ نفسِها: كلُّ check_*.py يجب أن يُنادى أعلاه
printf '\n\033[1m── كلُّ حارسٍ مربوطٌ بهذا الملفّ\033[0m\n'
missing=0
for f in .kiro/tools/check_*.py; do
  [ -e "$f" ] || continue
  name="$(basename "$f")"
  # تُحذف أسطرُ التعليقِ أوّلاً: حارسٌ يقرأ شرحَه هو كأنّه كودٌ يُبارك العطل
  if grep -v '^[[:space:]]*#' "$0" | grep -q "$name"; then
    echo "  ✓ $name مربوط"
  else
    echo "  ✗ $name موجودٌ في المستودعِ وغيرُ مربوط = صفرُ تأكيدات"
    missing=$((missing + 1))
  fi
done
if [ "$missing" -eq 0 ]; then
  pass=$((pass + 1))
else
  fail=$((fail + 1))
fi

printf '\n═══════════════════════════════════\n'
printf 'نجح %d · سقط %d\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
printf '\033[32mكلُّ الحوارسِ خضراء.\033[0m\n'
