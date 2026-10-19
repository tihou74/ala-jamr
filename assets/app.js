/* ===========================================================
   عالجمر — السلوك

   سكربت واحد غير وحدة (<script defer>) بقصد:
   في وحدة ESM، قراءة const قبل سطر تصريحه ترمي عند تقييم الوحدة
   فتتوقّف هناك ولا يُسنَد شيء بعدها — عطلٌ صامت قتل 107 دالّة في
   مشروع سابق. والـIIFE تُجنّبنا ذلك الشكل من الفشل.
   =========================================================== */

(function () {
  "use strict";

  var reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------------------------------------------------------
     مولّد عشوائي بذرة ثابتة.
     سرير الجمر يجب أن يكون هو نفسه في كل تحميل وفي كل لقطة
     تحقّق — وإلا صارت كل لقطة مقارنةً بمشهد آخر.
     --------------------------------------------------------- */
  function seeded(seed) {
    var s = seed >>> 0;
    return function () {
      s = (s * 1664525 + 1013904223) >>> 0;
      return s / 4294967296;
    };
  }

  function round2(n) {
    return Math.round(n * 100) / 100;
  }

  /* ---------------------------------------------------------
     سرير الجمر
     --------------------------------------------------------- */
  function buildEmbers(host) {
    if (!host) return 0;

    /* ظلالُ الفحمِ وقاعُ التوهّجِ صارا طبقتَي تدرّجٍ في ember.css، فلم يبقَ
       في DOM إلّا الشقوقُ الحارّةُ والشرارات. سببُ ذلك مُقاسٌ بلقطتَي شاشة:
       عشراتُ عناصرَ **فاتحةٍ** على خلفيّةٍ عاتمةٍ تُقرأ «كُراتٍ طافية»
       مرّتَين متتاليتَين، لا جمراً. والفحمُ ظِلٌّ أمام ضوءٍ لا ضوءٌ في عتمة. */
    var CRACKS = reduceMotion ? 0 : 11;
    var SPARKS = reduceMotion ? 0 : 12;

    var rnd = seeded(20261019);
    var frag = document.createDocumentFragment();
    var i;

    // شقوقٌ حارّةٌ بين الفحمات — قليلةٌ ومنخفضة
    for (i = 0; i < CRACKS; i++) {
      var c = document.createElement("i");
      c.className = "coal--crack";
      c.style.setProperty("--x", round2(5 + rnd() * 88) + "%");
      c.style.setProperty("--y", round2(2 + rnd() * 22) + "%");
      c.style.setProperty("--d", round2(22 + rnd() * 38) + "px");
      c.style.setProperty("--o", round2(0.5 + rnd() * 0.45));
      c.style.setProperty("--sp", round2(3 + rnd() * 4) + "s");
      c.style.setProperty("--dl", round2(rnd() * -6) + "s");
      frag.appendChild(c);
    }

    for (i = 0; i < SPARKS; i++) {
      var sp = document.createElement("i");
      sp.className = "spark";
      sp.style.setProperty("--x", round2(8 + rnd() * 84) + "%");
      sp.style.setProperty("--sp", round2(4 + rnd() * 5) + "s");
      sp.style.setProperty("--dl", round2(rnd() * -9) + "s");
      sp.style.setProperty("--drift", round2(-26 + rnd() * 52) + "px");
      frag.appendChild(sp);
    }

    host.appendChild(frag);
    return CRACKS + SPARKS;
  }

  /* ---------------------------------------------------------
     الكشف عند التمرير
     --------------------------------------------------------- */
  function initReveal() {
    var nodes = document.querySelectorAll("[data-reveal]");
    if (!nodes.length) return;

    // بلا IntersectionObserver: يُظهَر الكلّ فوراً.
    // احتياطٌ يُخفي المحتوى ليس احتياطاً.
    if (!("IntersectionObserver" in window)) {
      for (var k = 0; k < nodes.length; k++) nodes[k].classList.add("is-in");
      return;
    }

    var obs = new IntersectionObserver(
      function (entries) {
        for (var j = 0; j < entries.length; j++) {
          if (entries[j].isIntersecting) {
            entries[j].target.classList.add("is-in");
            obs.unobserve(entries[j].target);
          }
        }
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.08 }
    );

    for (var i = 0; i < nodes.length; i++) {
      // تدرّج داخل المجموعة الواحدة
      var group = nodes[i].parentNode;
      var idx = 0;
      if (group && group.hasAttribute && group.hasAttribute("data-reveal-stagger")) {
        idx = Array.prototype.indexOf.call(group.children, nodes[i]);
      }
      if (idx > 0) {
        nodes[i].style.setProperty("--reveal-delay", Math.min(idx, 8) * 80 + "ms");
      }
      obs.observe(nodes[i]);
    }
  }

  /* ---------------------------------------------------------
     حالة الشريط العلوي — بحارس لا بمستمع تمرير
     --------------------------------------------------------- */
  function initNav() {
    var nav = document.querySelector(".nav");
    var sentinel = document.querySelector("[data-nav-sentinel]");
    if (!nav) return;

    if (!sentinel || !("IntersectionObserver" in window)) {
      nav.classList.add("is-stuck");
      return;
    }

    new IntersectionObserver(
      function (entries) {
        nav.classList.toggle("is-stuck", !entries[0].isIntersecting);
      },
      { threshold: 0 }
    ).observe(sentinel);
  }

  /* ---------------------------------------------------------
     شريط متكرّر: تُضاعف المحتويات مرّة واحدة فيلتف بلا فجوة
     --------------------------------------------------------- */
  function initTicker() {
    var track = document.querySelector("[data-ticker]");
    if (!track || track.getAttribute("data-doubled") === "1") return;
    track.innerHTML = track.innerHTML + track.innerHTML;
    track.setAttribute("data-doubled", "1");
  }

  /* ---------------------------------------------------------
     سنة التذييل — تُقرأ من الجهاز ولا تُكتب حرفيّاً.
     تاريخٌ مكتوبٌ بالنصّ يصير تبعيّةً صامتةً تَبلى بلا إشعار.
     --------------------------------------------------------- */
  function initYear() {
    var slots = document.querySelectorAll("[data-year]");
    var y = String(new Date().getFullYear());
    for (var i = 0; i < slots.length; i++) slots[i].textContent = y;
  }

  /* ---------------------------------------------------------
     التشغيل: كل قطعة في try مستقلّة.
     سقوطُ واحدةٍ لا يُسقط البقيّة — وشلّالُ نداءاتٍ متتابعة
     في حلقة واحدة يجعل أوّلَ خطأٍ يقتل كلَّ ما بعده.
     --------------------------------------------------------- */
  function boot() {
    var steps = [
      ["embers", function () {
        return buildEmbers(document.querySelector("[data-embers]"));
      }],
      ["reveal", initReveal],
      ["nav", initNav],
      ["ticker", initTicker],
      ["year", initYear]
    ];

    for (var i = 0; i < steps.length; i++) {
      try {
        steps[i][1]();
      } catch (err) {
        // لا نُسكِت الخطأ: يُطبع باسم الخطوة فيُعرَف أيّها سقط
        if (window.console && console.warn) {
          console.warn("[alajamr] سقطت خطوة: " + steps[i][0], err);
        }
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
