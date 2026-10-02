(function () {
  'use strict';
  var root = document.documentElement;
  function get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } }

  document.getElementById('themeBtn').addEventListener('click', function () {
    var dark = root.getAttribute('data-theme') === 'dark' ||
      (!root.getAttribute('data-theme') && matchMedia('(prefers-color-scheme: dark)').matches);
    var next = dark ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('sb-theme', next); } catch (e) {}
  });

  var student = get('sb-student') || {};
  if (student.name) document.getElementById('hello').textContent = 'Вітаємо, ' + student.name + '!';

  // Прогрес учня з його браузера (ключі – як у app.js).
  JSON.parse(document.getElementById('lesson-data').textContent).forEach(function (L) {
    var saved = get(L.slug === 'slovo-bozhe' ? 'sb-results' : 'sb-results-' + L.slug) || {};
    var done = Object.keys(saved).filter(function (k) { return +k >= 1 && +k <= L.chapters; });
    if (!done.length) return;
    var avg = Math.round(done.reduce(function (s, k) { return s + (saved[k].best || saved[k].pct || 0); }, 0) / done.length);
    var el = document.querySelector('.lesson-card[data-lesson="' + L.slug + '"] .lc-prog');
    if (!el) return;
    el.textContent = 'Пройдено тестів: ' + done.length + ' з ' + L.chapters + ' · середній результат ';
    var b = document.createElement('b');
    b.textContent = avg + '%';
    el.appendChild(b);
  });
})();
