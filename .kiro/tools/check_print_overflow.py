#!/usr/bin/env python3
"""حارسُ القصِّ الصامت: لا محتوى يتجاوز ورقةَ A4 في profile.html.

لماذا هذا الحارسُ ضروريٌّ: صفحةُ البروفايل `height:297mm` مع
`overflow:hidden`. فسطرٌ واحدٌ زائدٌ **يُقَصّ بلا أيِّ رسالة** — لا خطأٌ
في وحدةِ التحكّم ولا تحذيرٌ في التوليد، والـPDF يُفتَح ويبدو سليماً
وآخرُ كلمةٍ في الصفحةِ مبتورة. وهذا أسوأُ أنواعِ الأعطال: المالكُ يُقدّم
الملفَّ لمالكِ عقارٍ وفيه فقرةٌ مقطوعةٌ في منتصفها.

كيف يُقاس: يُفتَح الملفُّ بمحاكاةِ الطباعة، ويُقارَن أسفلُ **كلِّ** عنصرٍ
داخلَ الصفحةِ بأسفلِ الورقة. وأيُّ تجاوزٍ فوق حدِّ التسامحِ يُسقِط التشغيل.

ومُجرَّبٌ بكسرِ نسخة: حُشِي نصٌّ في الصفحةِ الثالثةِ فأبلغ `+862px`،
والنسخةُ السليمةُ صفرٌ في الاثنتَي عشرةَ كلِّها. فالمقياسُ يُفرّق.

الاستخدام: python3 .kiro/tools/check_print_overflow.py [profile.html]
رمز الخروج: 0 سليم · 2 محتوى مقصوص · 1 خطأ في الحارس
"""
import json
import os
import re
import subprocess
import sys
import tempfile

SHELL = ("/inner_container/opt/playwright/chromium_headless_shell-1232/"
         "chrome-headless-shell-linux64/chrome-headless-shell")
TOLERANCE = 2          # بكسلانِ للتقريب الفرعي
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

INJECT = """
<style>.screen-only{display:none!important}body{padding:0!important}</style>
<script>
window.addEventListener('load',function(){
  var out=[];
  document.querySelectorAll('.page').forEach(function(p,i){
    var pr=p.getBoundingClientRect();
    var worst=0, who='';
    p.querySelectorAll('*').forEach(function(el){
      var r=el.getBoundingClientRect();
      if(r.height>0){
        var d=Math.round(r.bottom-pr.bottom);
        if(d>worst){ worst=d; who=el.className||el.tagName; }
      }
    });
    out.push({page:i+1, over:worst, el:String(who).slice(0,40)});
  });
  var el=document.createElement('pre'); el.id='report';
  el.textContent=JSON.stringify(out); document.body.appendChild(el);
});
</script>
"""


def measure(path):
    with open(path, encoding="utf-8") as fh:
        html = fh.read()
    if "</head>" not in html:
        print("خطأ في الحارس: لا <head> في الملفّ.", file=sys.stderr)
        return None
    if 'class="page' not in html:
        print("خطأ في الحارس: صفرُ عناصرَ .page — لم يُفحَص شيء.",
              file=sys.stderr)
        return None

    with tempfile.TemporaryDirectory(dir=ROOT) as d:
        probe = os.path.join(d, "probe.html")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write(html.replace("</head>", INJECT + "</head>"))
        res = subprocess.run(
            [SHELL, "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
             "--allow-file-access-from-files",
             "--user-data-dir=/projects/sandbox/.cp-shell",
             "--virtual-time-budget=9000", "--dump-dom", "file://" + probe],
            capture_output=True, text=True, timeout=180)
    m = re.search(r'<pre id="report">(.*?)</pre>', res.stdout, re.S)
    if not m:
        print("خطأ في الحارس: لم يُقرأ التقريرُ من المتصفّح.", file=sys.stderr)
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        print("خطأ في الحارس: تقريرٌ غيرُ مفهوم.", file=sys.stderr)
        return None


def main(argv):
    path = argv[1] if len(argv) > 1 else os.path.join(ROOT, "profile.html")
    if not os.path.isfile(path):
        print(f"لا يوجد {path} — لا شيءَ لفحصه.")
        return 0

    data = measure(path)
    if data is None:
        return 1
    if not data:
        print("خطأ في الحارس: صفرُ صفحاتٍ مقيسة.", file=sys.stderr)
        return 1

    bad = [d for d in data if d["over"] > TOLERANCE]
    print(f"فُحِصت {len(data)} صفحةً في {os.path.basename(path)}")
    for d in data:
        if d["over"] > TOLERANCE:
            print(f"  BLOCK صفحة {d['page']}: المحتوى يتجاوز الورقةَ بـ"
                  f"{d['over']}px — العنصر «{d['el']}» يُقَصّ بلا رسالة",
                  file=sys.stderr)

    if bad:
        print(f"\nسقط الحارس: {len(bad)} صفحةً فيها محتوىً مقصوص.",
              file=sys.stderr)
        return 2
    print(f"سليم: صفرُ قصٍّ في {len(data)} صفحة.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
