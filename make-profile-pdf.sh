#!/usr/bin/env bash
# ===========================================================
# توليدُ بروفايل عالجمر PDF من profile.html
#
#   bash make-profile-pdf.sh
#   => docs/ALAJAMR-PROFILE.pdf
#
# ولماذا يَخرج العربيُّ سليماً من هنا: ملفّاتُ الخطِّ **مستضافةٌ في
# المستودع** (`assets/fonts/`)، فيُدمجها المتصفّحُ في الـPDF. وقبل
# استضافتِها كان الملفُّ يَخرج بصفرِ خطوطٍ مُدمجةٍ وعربيُّه فارغ.
#
# ويُستعمل `chrome-headless-shell` لا `chrome`: الثاني يفشل في هذا
# الصندوق بـ`chrome_crashpad_handler: --database is required`، ولا
# تُصلحه `--crash-dumps-dir` ولا `--disable-crash-reporter` ولا
# `--headless=new` (جُرِّبت الخمس).
# ===========================================================
set -euo pipefail
cd "$(dirname "$0")"

SHELL_BIN="/inner_container/opt/playwright/chromium_headless_shell-1232/chrome-headless-shell-linux64/chrome-headless-shell"
SRC="profile.html"
OUT="docs/ALAJAMR-PROFILE.pdf"
MIN_PAGES=10

[ -f "$SRC" ] || { echo "لا يوجد $SRC" >&2; exit 1; }
[ -x "$SHELL_BIN" ] || { echo "لا متصفّحَ عند $SHELL_BIN" >&2; exit 1; }

mkdir -p docs
rm -f "$OUT"

echo "== توليد $OUT =="
"$SHELL_BIN" \
  --no-sandbox --disable-gpu --disable-dev-shm-usage \
  --allow-file-access-from-files \
  --user-data-dir=/projects/sandbox/.cp-shell \
  --print-to-pdf-no-header \
  --print-to-pdf="$PWD/$OUT" \
  --virtual-time-budget=15000 \
  "file://$PWD/$SRC" 2>&1 | grep -i "written" || true

[ -f "$OUT" ] || { echo "فشل: لم يُنتَج الملفّ" >&2; exit 1; }

echo
echo "== التحقّق =="
python3 .kiro/tools/pdfpages.py "$OUT" "$MIN_PAGES"
code=$?

# خطٌّ مُدمَجٌ شرطٌ لا زينة: بلا خطوطٍ مُدمجةٍ يَخرج العربيُّ فارغاً،
# والملفُّ يُفتَح ويبدو سليماً — وهذا أسوأُ من فشلٍ معلَن.
fonts=$(python3 - "$OUT" <<'PY'
import sys
print(open(sys.argv[1],'rb').read().count(b'/FontFile'))
PY
)
if [ "$fonts" -lt 1 ]; then
  echo "سقط: صفرُ خطوطٍ مُدمجةٍ — سيَخرج العربيُّ فارغاً." >&2
  echo "تحقّق أنّ assets/fonts/*.ttf موجودةٌ وأنّ tokens.css يقرؤها." >&2
  exit 2
fi
echo "  خطوطٌ مُدمجة: $fonts  ✅ العربيُّ سيُرسَم"
exit $code
