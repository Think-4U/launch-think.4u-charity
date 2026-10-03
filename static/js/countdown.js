/**
 * countdown.js — Think4U Launch Page Countdown Timer
 * Reads data-* attributes from the #countdown-root element.
 * Zero dependency — pure vanilla JS.
 */

(function () {
  "use strict";

  const root = document.getElementById("countdown-root");
  if (!root) return;

  // Read config from data attributes set by Flask/Jinja
  const targetUTC   = root.dataset.target;        // e.g. "2027-01-26T03:30:00Z"
  const autoRedirect= root.dataset.autoRedirect === "true";
  const redirectUrl = root.dataset.redirectUrl    || "https://think4u.org";
  const redirectDelay = parseInt(root.dataset.redirectDelay || "5", 10);

  const targetMs = new Date(targetUTC).getTime();

  // DOM references
  const daysEl    = document.getElementById("cd-days");
  const hoursEl   = document.getElementById("cd-hours");
  const minsEl    = document.getElementById("cd-minutes");
  const secsEl    = document.getElementById("cd-seconds");
  const daysNum   = document.getElementById("cd-days-num");
  const hoursNum  = document.getElementById("cd-hours-num");
  const minsNum   = document.getElementById("cd-minutes-num");
  const secsNum   = document.getElementById("cd-seconds-num");
  const launchMsg = document.getElementById("launch-message");
  const cdGrid    = document.getElementById("countdown-grid");

  let prevValues = { d: -1, h: -1, m: -1, s: -1 };
  let redirecting = false;

  function pad(n) {
    return String(Math.max(0, n)).padStart(2, "0");
  }

  function animatePop(el) {
    if (!el) return;
    el.classList.remove("cd-pop");
    // Force reflow so animation re-triggers
    void el.offsetWidth;
    el.classList.add("cd-pop");
  }

  function updateDisplay(d, h, m, s) {
    if (d !== prevValues.d) { if (daysNum)  { daysNum.textContent  = pad(d); animatePop(daysEl);  } }
    if (h !== prevValues.h) { if (hoursNum) { hoursNum.textContent = pad(h); animatePop(hoursEl); } }
    if (m !== prevValues.m) { if (minsNum)  { minsNum.textContent  = pad(m); animatePop(minsEl);  } }
    if (s !== prevValues.s) { if (secsNum)  { secsNum.textContent  = pad(s); animatePop(secsEl);  } }
    prevValues = { d, h, m, s };
  }

  function showLaunchMessage() {
    if (cdGrid)    cdGrid.style.display    = "none";
    if (launchMsg) launchMsg.style.display = "flex";
  }

  function tick() {
    const now = Date.now();
    const diff = targetMs - now;

    if (diff <= 0) {
      updateDisplay(0, 0, 0, 0);
      showLaunchMessage();

      if (autoRedirect && !redirecting) {
        redirecting = true;
        const delayMsg = document.getElementById("redirect-delay-msg");
        let countdown = redirectDelay;
        if (delayMsg) delayMsg.textContent = `Redirecting in ${countdown}s…`;
        const iv = setInterval(() => {
          countdown--;
          if (delayMsg) delayMsg.textContent = `Redirecting in ${countdown}s…`;
          if (countdown <= 0) {
            clearInterval(iv);
            window.location.href = redirectUrl;
          }
        }, 1000);
      }
      return; // Stop ticking
    }

    const totalSecs = Math.floor(diff / 1000);
    const s = totalSecs % 60;
    const totalMins = Math.floor(totalSecs / 60);
    const m = totalMins % 60;
    const totalHours = Math.floor(totalMins / 60);
    const h = totalHours % 24;
    const d = Math.floor(totalHours / 24);

    updateDisplay(d, h, m, s);
    setTimeout(tick, 1000 - (Date.now() % 1000)); // Align to clock second boundary
  }

  // Handle tab visibility changes (correct drift when tab is brought back)
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") tick();
  });

  // Kick off
  tick();
})();
