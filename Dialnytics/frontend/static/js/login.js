/* Sign-in page: cursor spotlight, parallax and card tilt (CSS variables), wave bars, password toggle. */
(function () {
  'use strict';
  var page = document.querySelector('.lg-page');
  if (!page) return;

  // wave bars
  var wave = document.getElementById('lgWave');
  if (wave) {
    for (var i = 0; i < 28; i++) {
      var s = document.createElement('span');
      var w = Math.abs(Math.sin(i * 0.55)) * 0.7 + 0.3;
      s.style.height = Math.round(54 * w) + 'px';
      s.style.opacity = (0.55 + w * 0.45).toFixed(2);
      s.style.animationDelay = (i * 0.07).toFixed(2) + 's';
      wave.appendChild(s);
    }
  }

  // cursor effects (skipped for reduced motion and touch-only devices)
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = window.matchMedia && matchMedia('(pointer: fine)').matches;
  if (!reduce && fine) {
    var raf = 0, nx = 0, ny = 0, px = -999, py = -999;
    function paint() {
      raf = 0;
      page.style.setProperty('--mx', px + 'px');
      page.style.setProperty('--my', py + 'px');
      page.style.setProperty('--dx', nx.toFixed(3));
      page.style.setProperty('--dy', ny.toFixed(3));
    }
    function schedule() { if (!raf) raf = requestAnimationFrame(paint); }
    page.addEventListener('mousemove', function (e) {
      var r = page.getBoundingClientRect();
      px = Math.round(e.clientX - r.left);
      py = Math.round(e.clientY - r.top);
      nx = (e.clientX - r.left) / r.width - 0.5;
      ny = (e.clientY - r.top) / r.height - 0.5;
      schedule();
    });
    page.addEventListener('mouseleave', function () { px = py = -999; nx = ny = 0; schedule(); });
  }

  // show / hide password
  var eye = document.getElementById('lgEye'), pw = document.getElementById('lgPass');
  if (eye && pw) {
    eye.addEventListener('click', function () {
      var show = pw.type === 'password';
      pw.type = show ? 'text' : 'password';
      eye.textContent = show ? 'Hide' : 'Show';
      pw.focus();
    });
  }

  // avoid double submits
  var form = document.getElementById('lgForm'), btn = document.getElementById('lgSubmit');
  if (form && btn) {
    form.addEventListener('submit', function () {
      btn.disabled = true;
      btn.textContent = 'Signing in…';
    });
    window.addEventListener('pageshow', function (e) {   // back button after a failed attempt
      if (e.persisted) { btn.disabled = false; btn.textContent = 'Sign in'; }
    });
  }
})();
