(function () {
  var canvas = document.getElementById('dots');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');

  var s = canvas.style;
  s.position = 'fixed';
  s.left = '0';
  s.bottom = '-50px';
  s.display = 'block';
  s.zIndex = '-1';
  s.pointerEvents = 'none';
  canvas.setAttribute('aria-hidden', 'true');

  var ROWS = 7, LEVELS = 6;
  var accent = (getComputedStyle(document.documentElement).getPropertyValue('--accent') || '').trim() || '#4da6ff';

  var seed = (Math.random() * 4294967296) >>> 0;
  function rng() {
    seed = (seed + 0x6D2B79F5) >>> 0;
    var t = seed;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  var waves = [];
  for (var i = 0; i < 4; i++) {
    waves.push({
      fx: 0.03 + rng() * 0.12,
      fy: 0.15 + rng() * 0.35,
      px: rng() * 6.283,
      py: rng() * 6.283,
      w: 0.6 + rng() * 0.8
    });
  }
  var grainSeed = (rng() * 4294967296) >>> 0;
  function grain(c, r) {
    var h = (Math.imul(c + 1, 374761393) ^ Math.imul(r + 1, 668265263) ^ grainSeed) >>> 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177) >>> 0;
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }

  function colReach(c) {
    var s1 = 0.5 + 0.5 * Math.sin(c * 0.55 + waves[0].px);
    var s2 = 0.5 + 0.5 * Math.sin(c * 1.35 + waves[1].py);
    return 0.3 + 0.7 * (0.35 * s1 + 0.25 * s2 + 0.4 * grain(c, 999));
  }

  function draw() {
    var w = document.documentElement.clientWidth;
    if (!w) return;

    var target = w < 640 ? 26 : 32;
    var cols = Math.max(1, Math.round(w / target));
    var cell = w / cols;
    var radius = cell * 0.34;
    var h = Math.round(ROWS * cell);

    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    canvas.style.opacity = 0.5;

    var dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = accent;

    for (var r = 0; r < ROWS; r++) {
      var rowT = r / (ROWS - 1);
      for (var c = 0; c < cols; c++) {
        var v = 0, total = 0;
        for (var k = 0; k < waves.length; k++) {
          var wv = waves[k];
          v += wv.w * (0.5 + 0.5 * Math.sin(c * wv.fx * 2 + r * wv.fy + wv.px + wv.py * rowT));
          total += wv.w;
        }
        v = v / total;
        v = v * 0.7 + grain(c, r) * 0.45;

        var edge = (rowT - (1 - colReach(c))) / 0.45;
        if (edge <= 0) continue;
        if (edge < 0.6 && grain(c, r + 500) > 0.55) continue;
        v = v * (0.5 + 0.7 * rowT);

        var level = Math.max(0, Math.min(LEVELS - 1, Math.floor(v * LEVELS * 1.15)));
        ctx.globalAlpha = (0.14 + (level / (LEVELS - 1)) * 0.86) * Math.min(1, edge * 1.2);
        ctx.beginPath();
        ctx.arc(c * cell + cell / 2, r * cell + cell / 2, radius, 0, 6.2832);
        ctx.fill();
      }
    }
    ctx.globalAlpha = 1;
  }

  draw();
  window.addEventListener('resize', draw);
})();
