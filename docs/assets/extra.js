/* Growth Factors portal - interaction + motion layer.
   Runs on first load and on every Material instant-navigation. Honours
   prefers-reduced-motion and degrades gracefully when JS is unavailable
   (numbers and meters are authored at their real values in the HTML). */

(function () {
  "use strict";

  var reduce = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

  function countUp(el) {
    var target = parseFloat(el.getAttribute("data-count"));
    if (isNaN(target)) return;
    if (reduce) { el.textContent = String(target); return; }
    var start = null, dur = 900;
    el.textContent = "0";
    function step(ts) {
      if (start === null) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      el.textContent = String(Math.round(target * easeOut(p)));
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function fillMeter(el) {
    var target = el.getAttribute("data-target");
    if (target === null) return;
    if (reduce) { el.style.width = target + "%"; return; }
    el.style.width = "0%";
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { el.style.width = target + "%"; });
    });
  }

  function fillRing(ring) {
    var target = parseFloat(getComputedStyle(ring).getPropertyValue("--v"));
    if (isNaN(target)) return;
    if (reduce) { ring.style.setProperty("--v", target); return; }
    var start = null, dur = 1000;
    ring.style.setProperty("--v", 0);
    function step(ts) {
      if (start === null) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      ring.style.setProperty("--v", (target * easeOut(p)).toFixed(2));
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function animateSection(sec) {
    sec.querySelectorAll("[data-count]").forEach(countUp);
    sec.querySelectorAll(".gf-meter__fill[data-target]").forEach(fillMeter);
    sec.querySelectorAll(".gf-ring[style*='--v']").forEach(fillRing);
  }

  function setupReveal(root) {
    var items = root.querySelectorAll(".gf-reveal");
    if (!items.length) return;
    if (reduce || !("IntersectionObserver" in window)) {
      items.forEach(function (el) { el.classList.add("is-in"); animateSection(el); });
      return;
    }
    var io = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("is-in");
          animateSection(e.target);
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.18, rootMargin: "0px 0px -8% 0px" });
    items.forEach(function (el) { io.observe(el); });
  }

  function setupTimeline(root) {
    var spines = root.querySelectorAll(".gf-spine");
    spines.forEach(function (spine) {
      var tabs = spine.querySelectorAll(".gf-phase");
      var panels = spine.parentElement.querySelectorAll(".gf-phase-panel");
      function select(idx) {
        tabs.forEach(function (t, i) {
          var on = i === idx;
          t.setAttribute("aria-selected", on ? "true" : "false");
          t.setAttribute("tabindex", on ? "0" : "-1");
        });
        panels.forEach(function (p, i) {
          if (i === idx) p.removeAttribute("hidden");
          else p.setAttribute("hidden", "");
        });
      }
      function go(next) {
        if (next < 0) next = tabs.length - 1;
        if (next >= tabs.length) next = 0;
        tabs[next].focus();
        select(next);
      }
      tabs.forEach(function (tab, i) {
        tab.addEventListener("click", function () { select(i); });
        tab.addEventListener("keydown", function (ev) {
          if (ev.key === "ArrowRight") { ev.preventDefault(); go(i + 1); }
          else if (ev.key === "ArrowLeft") { ev.preventDefault(); go(i - 1); }
          else if (ev.key === "Home") { ev.preventDefault(); go(0); }
          else if (ev.key === "End") { ev.preventDefault(); go(tabs.length - 1); }
        });
      });
      // Establish roving tabindex from the initially selected tab.
      var cur = 0;
      tabs.forEach(function (t, i) { if (t.getAttribute("aria-selected") === "true") cur = i; });
      select(cur);
    });
  }

  function markHome(root) {
    // Widen the content column only on the dashboard home page.
    var body = document.body;
    if (root.querySelector(".gf-cockpit")) body.classList.add("gf-home");
    else body.classList.remove("gf-home");
  }

  function init() {
    try {
      document.documentElement.classList.add("gf-js");
      var root = document.querySelector(".md-content") || document;
      markHome(root);
      setupReveal(root);
      setupTimeline(root);
    } catch (e) {
      // Fail open: never let a JS error leave the dashboard blank.
      document.querySelectorAll(".gf-reveal").forEach(function (el) {
        el.classList.add("is-in");
      });
      if (window.console && console.error) console.error("gf portal init:", e);
    }
  }

  // Wrap the subscription so a throw can never tear down document$ and blank
  // every subsequent instant-navigation page.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(function () { init(); });
  } else if (document.readyState !== "loading") {
    init();
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }
})();
