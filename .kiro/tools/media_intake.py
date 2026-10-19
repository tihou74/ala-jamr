#!/usr/bin/env python3
"""استلامُ موادِّ المالكِ الحقيقيّة: جردٌ · تسميةٌ لاتينيّة · نسخُ مراجعة.

يُشغَّل بعد كلِّ رفعة:  python3 .kiro/tools/media_intake.py

ما يفعله:
  1. يمسح `inbox/` **وجذرَ المستودع** — المالكُ يرفع إلى الجذرِ عادةً ولو
     أُعطي رابطَ المجلّدِ المباشر، فالاقتصارُ على `inbox/` يُبلّغ «لم يصل شيء»
     وهو قد رفع فعلاً.
  2. يَجرُد كلَّ ملفّ: النوع · الحجم · الأبعاد (للصور) · مدّة (إن عُرفت)
  3. يُنبّه على الأسماءِ العربيّةِ أو ذاتِ المسافاتِ أو الامتدادِ المزدوج
     (`.mp3.mpeg`) — تنكسر في مساراتِ URL على GitHub Pages
  4. يُنتج **نسخةَ مراجعةٍ** لكلِّ صورةٍ بحدٍّ أقصى 1600 بكسل في
     `docs/review/` — فالأصلُ من الهاتفِ غالباً 3000–4000 بكسلاً ولا تجوز
     قراءتُه (حدُّ 2000 بكسل، والرفضُ يأتي بعد انتهاء العمل فتضيع الجلسة)

قيودٌ مقيسةٌ في هذا الصندوق — تُقال ولا تُكتم:
  · `ffmpeg` المتاح مبنيٌّ لأغراضِ playwright: يفكّ **VP8/WebM فقط**.
    صفرُ مفكِّكات h264/hevc وصفرُ صِيَغ mp4/mov ⇒ **فيديو الهاتفِ لا يُفكّ**،
    فلا إطاراتٌ ولا معاينةٌ منه. ويبقى صالحاً تماماً للعرضِ في الموقع.
  · فكُّ JPEG يمرّ عبر **المتصفّح** لا ffmpeg (جُرِّب ffmpeg على JPEG حقيقيّةٍ
    فسقط بـ"Invalid data found"). المتصفّحُ نجح: 550x629 ⇒ 400x458.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REVIEW = os.path.join(ROOT, "docs", "review")
SHELL = ("/inner_container/opt/playwright/chromium_headless_shell-1232/"
         "chrome-headless-shell-linux64/chrome-headless-shell")

MAX_REVIEW = 1600          # حدُّ نسخةِ المراجعة
HARD_LIMIT = 2000          # الحدُّ الذي تُرفَض القراءةُ فوقه
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif", ".avif"}
VID_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".3gp", ".hevc"}
AUD_EXT = {".mp3", ".m4a", ".wav", ".aac", ".ogg"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".kiro", "assets",
             "docs", ".tmp"}

ARABIC = re.compile(r"[\u0600-\u06FF]")

TRANSLIT = {
    "ا": "a", "أ": "a", "إ": "i", "آ": "aa", "ب": "b", "ت": "t", "ث": "th",
    "ج": "j", "ح": "h", "خ": "kh", "د": "d", "ذ": "dh", "ر": "r", "ز": "z",
    "س": "s", "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "a",
    "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n",
    "ه": "h", "و": "w", "ي": "y", "ى": "a", "ة": "h", "ء": "", "ئ": "y",
    "ؤ": "w", "َ": "", "ُ": "", "ِ": "", "ّ": "", "ْ": "", "ٌ": "", "ً": "",
    "ٍ": "",
}


def latinize(name):
    stem, ext = os.path.splitext(name)
    out = []
    for ch in stem:
        if ch in TRANSLIT:
            out.append(TRANSLIT[ch])
        elif ARABIC.match(ch):
            out.append("")
        elif ch.isalnum():
            out.append(ch.lower())
        else:
            out.append("-")
    s = "".join(out)
    s = re.sub(r"-{2,}", "-", s).strip("-") or "file"
    return s + ext.lower()


def png_size(path):
    try:
        with open(path, "rb") as fh:
            head = fh.read(33)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        import struct
        w, h = struct.unpack(">II", head[16:24])
        return w, h
    except Exception:
        return None


def jpeg_size(path):
    """أبعادُ JPEG من ترويسةِ SOF بلا مكتبةٍ خارجيّة."""
    try:
        with open(path, "rb") as fh:
            if fh.read(2) != b"\xff\xd8":
                return None
            while True:
                b = fh.read(1)
                if not b:
                    return None
                if b != b"\xff":
                    continue
                marker = fh.read(1)
                while marker == b"\xff":
                    marker = fh.read(1)
                if not marker:
                    return None
                m = marker[0]
                if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                    continue
                ln = fh.read(2)
                if len(ln) < 2:
                    return None
                length = (ln[0] << 8) + ln[1]
                if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                    data = fh.read(5)
                    if len(data) < 5:
                        return None
                    h = (data[1] << 8) + data[2]
                    w = (data[3] << 8) + data[4]
                    return w, h
                fh.seek(length - 2, 1)
    except Exception:
        return None


def sniff(path):
    """نوعُ الصورةِ من **بصمةِ البايتات** لا من الامتداد.

    الامتدادُ يكذب — وهذا مقيسٌ لا مُتوقَّع: ملفّان في موادِّ مشروعٍ سابقٍ
    اسمُهما `.jpg` وهما PNG فعلاً، فسقط مُحلِّلُ JPEG عليهما وأُعلنت
    الأبعادُ «غير مقروءة»، ثمّ صُنعت نسخةُ مراجعةٍ **مربّعةٍ مشوّهة**.
    """
    try:
        with open(path, "rb") as fh:
            h = fh.read(16)
    except OSError:
        return None
    if h[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if h[:2] == b"\xff\xd8":
        return "jpeg"
    if h[:4] == b"RIFF" and h[8:12] == b"WEBP":
        return "webp"
    if h[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if h[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1", b"ftyphevc"):
        return "heic"
    return None


def webp_size(path):
    try:
        with open(path, "rb") as fh:
            d = fh.read(32)
        if d[12:16] == b"VP8X":
            w = 1 + int.from_bytes(d[24:27], "little")
            h = 1 + int.from_bytes(d[27:30], "little")
            return w, h
        if d[12:16] == b"VP8 ":
            import struct
            w, h = struct.unpack("<HH", d[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if d[12:16] == b"VP8L":
            b = int.from_bytes(d[21:25], "little")
            return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    except Exception:
        return None
    return None


def gif_size(path):
    try:
        with open(path, "rb") as fh:
            d = fh.read(10)
        import struct
        return struct.unpack("<HH", d[6:10])
    except Exception:
        return None


def dims(path):
    kind = sniff(path)
    if kind == "png":
        return png_size(path)
    if kind == "jpeg":
        return jpeg_size(path)
    if kind == "webp":
        return webp_size(path)
    if kind == "gif":
        return gif_size(path)
    return None   # HEIC وغيرُه: الأبعادُ غيرُ مقروءةٍ هنا


def make_review(src, out, max_dim):
    """نسخةُ مراجعةٍ عبر المتصفّح — ffmpeg المتاحُ لا يفكّ JPEG."""
    d = dims(src)
    if d:
        w, h = d
        scale = min(1.0, max_dim / max(w, h))
        vw, vh = max(40, int(w * scale)), max(40, int(h * scale))
    else:
        # لا تُصنَع نسخةٌ مربّعةٌ عند جهلِ الأبعاد: تُشوّه الصورةَ أو تُحيط
        # بها بإطارٍ أسودَ فيُحكَم على التأطيرِ بما ليس فيها.
        return None, ("أبعادٌ غير مقروءة (الصيغةُ غيرُ مدعومةٍ هنا — HEIC؟) — "
                      "لا تُصنَع نسخةُ مراجعةٍ بالظنّ. "
                      "حوّلها إلى JPEG أو PNG قبل الرفع.")

    if vw > HARD_LIMIT or vh > HARD_LIMIT:
        return None, f"مرفوض: نسخةُ المراجعةِ {vw}x{vh} تتجاوز {HARD_LIMIT}"

    html = os.path.join(ROOT, ".tmp-review.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(html, "w", encoding="utf-8") as fh:
        fh.write('<!doctype html><html><body style="margin:0;background:#111">'
                 f'<img src="file://{os.path.abspath(src)}" '
                 f'style="display:block;width:{vw}px;height:auto">'
                 "</body></html>")
    subprocess.run(
        [SHELL, "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
         "--disable-dev-shm-usage", "--allow-file-access-from-files",
         "--user-data-dir=/projects/sandbox/.cp-shell",
         f"--window-size={vw},{vh}", "--virtual-time-budget=3000",
         f"--screenshot={os.path.abspath(out)}",
         "file://" + html],
        capture_output=True, timeout=120)
    try:
        os.remove(html)
    except OSError:
        pass
    if not os.path.isfile(out):
        return None, "فشل: المتصفّحُ لم يُنتج نسخةَ مراجعة"
    return dims(out), None


def human(n):
    for unit in ("B", "K", "M", "G"):
        if n < 1024 or unit == "G":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n/1:.0f}{unit}" \
                if False else f"{n:.1f}{unit}".replace(".0", "")
        n /= 1024.0


def collect():
    """inbox/ **وجذرُ المستودع** — المالكُ يرفع إلى الجذرِ عادةً."""
    found = []
    inbox = os.path.join(ROOT, "inbox")
    if os.path.isdir(inbox):
        for dirpath, dirnames, filenames in os.walk(inbox):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for n in filenames:
                if not n.startswith("."):
                    found.append(os.path.join(dirpath, n))
    for n in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, n)
        if os.path.isfile(p) and not n.startswith("."):
            ext = os.path.splitext(n)[1].lower()
            if ext in IMG_EXT | VID_EXT | AUD_EXT:
                found.append(p)
    return sorted(set(found))


def main(argv):
    do_rename = "--rename" in argv
    files = collect()

    if not files:
        print("لم يصل شيءٌ بعد.")
        print("فُحِص: inbox/ **وجذرُ المستودع** (المالكُ يرفع إلى الجذرِ عادةً).")
        print("هذه ليست رسالةَ خطأ — المجلّدُ فارغٌ فعلاً.")
        return 0

    imgs, vids, auds, other = [], [], [], []
    for p in files:
        ext = os.path.splitext(p)[1].lower()
        (imgs if ext in IMG_EXT else
         vids if ext in VID_EXT else
         auds if ext in AUD_EXT else other).append(p)

    print(f"══ وصل {len(files)} ملفّاً ══")
    print(f"   صور {len(imgs)} · فيديو {len(vids)} · صوت {len(auds)} "
          f"· أخرى {len(other)}\n")

    warnings = []
    renames = []

    def report(group, label):
        if not group:
            return
        print(f"── {label} ──")
        for p in group:
            rel = os.path.relpath(p, ROOT)
            size = os.path.getsize(p)
            name = os.path.basename(p)
            d = dims(p)
            dtxt = f"{d[0]}x{d[1]}" if d else "أبعاد غير مقروءة"
            flag = ""
            if d and max(d) > HARD_LIMIT:
                flag = f"  ⚠ يتجاوز {HARD_LIMIT} — تُصنَع نسخةُ مراجعة"
            print(f"  {rel}")
            print(f"      {size/1024:.0f} ك.ب · {dtxt}{flag}")

            if ARABIC.search(name):
                warnings.append(f"اسمٌ عربيّ: {rel} — ينكسر في مسارِ URL")
                renames.append(p)
            elif " " in name:
                warnings.append(f"مسافةٌ في الاسم: {rel}")
                renames.append(p)
            elif name.count(".") > 1:
                warnings.append(f"امتدادٌ مزدوج: {rel}")
            if os.path.dirname(p) == ROOT:
                warnings.append(f"في جذرِ المستودعِ لا في inbox/: {rel}")
        print()

    report(imgs, "الصور")
    report(vids, "الفيديو")
    report(auds, "الصوت")
    report(other, "أخرى")

    # نسخُ المراجعة
    if imgs:
        print("── نسخُ المراجعة (≤ "
              f"{MAX_REVIEW} بكسلاً، في docs/review/) ──")
        made = 0
        for p in imgs:
            out = os.path.join(REVIEW, latinize(os.path.basename(p))
                               .rsplit(".", 1)[0] + ".png")
            d, err = make_review(p, out, MAX_REVIEW)
            if err:
                print(f"  ✗ {os.path.basename(p)} — {err}")
            else:
                print(f"  ✓ {os.path.relpath(out, ROOT)}  {d[0]}x{d[1]}")
                made += 1
        print(f"  {made} من {len(imgs)}\n")

    if vids:
        print("── الفيديو: ما أقدر عليه وما لا أقدر ──")
        print("  ✓ يُعرَض في الموقعِ بلا مشكلة — المتصفّحُ يفكّه لا أنا")
        print("  ✗ **لا أستطيع رؤيتَه**: ffmpeg في هذا الصندوقِ مبنيٌّ "
              "لأغراضِ playwright")
        print("     (صفرُ مفكِّكات h264/hevc · صفرُ صِيَغ mp4/mov · "
              "VP8/WebM فقط)")
        print("  ⇒ فصِف لي كلَّ مقطعٍ بسطرٍ واحد، أو أرسِل لقطةً منه، "
              "وأنا أضعه في موضعِه\n")

    if renames and do_rename:
        print("── التسميةُ اللاتينيّة ──")
        for p in renames:
            new = os.path.join(os.path.dirname(p),
                               latinize(os.path.basename(p)))
            if os.path.abspath(new) == os.path.abspath(p):
                continue
            if os.path.exists(new):
                print(f"  ✗ موجودٌ سلفاً: {os.path.basename(new)}")
                continue
            os.rename(p, new)
            print(f"  {os.path.basename(p)}  ->  {os.path.basename(new)}")
        print()
    elif renames:
        print(f"── {len(renames)} ملفّاً يحتاج تسميةً لاتينيّة ──")
        print("   شغّل:  python3 .kiro/tools/media_intake.py --rename\n")

    if warnings:
        print("── تنبيهات ──")
        for w in dict.fromkeys(warnings):
            print(f"  ⚠ {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
