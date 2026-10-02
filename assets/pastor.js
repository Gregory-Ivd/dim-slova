(function () {
  'use strict';
  var root = document.documentElement;
  function $(s, el) { return (el || document).querySelector(s); }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function ls(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  $('#themeBtn').addEventListener('click', function () {
    var dark = root.getAttribute('data-theme') === 'dark' ||
      (!root.getAttribute('data-theme') && matchMedia('(prefers-color-scheme: dark)').matches);
    var next = dark ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    ls('sb-theme', next);
  });

  var qd = $('#quiz-data');
  var ENDPOINT = qd.getAttribute('data-endpoint') || '';
  var QUIZ = JSON.parse(qd.textContent);
  var CH = QUIZ.map(function (d) { return d.chapter; });
  var byCh = {};
  QUIZ.forEach(function (d) { byCh[d.chapter] = d; });

  var m = location.hash.match(/key=([^&]+)/);
  var KEY = m ? decodeURIComponent(m[1]) : ls('sb-pkey');
  if (m) ls('sb-pkey', KEY);

  var status = $('#status');
  function setStatus(t, err) { status.textContent = t; status.className = 'p-status' + (err ? ' err' : ''); }
  function cls(p) { return p >= 85 ? 'g' : p >= 60 ? 'y' : 'r'; }
  function fmtDate(iso, withTime) {
    var d = new Date(iso);
    if (isNaN(d)) return '';
    var o = { day: 'numeric', month: 'short' };
    if (d.getFullYear() !== new Date().getFullYear()) o.year = 'numeric';
    if (withTime) { o.hour = '2-digit'; o.minute = '2-digit'; }
    return d.toLocaleString('uk-UA', o);
  }
  function norm(n) { return String(n).toLowerCase().replace(/[’'`ʼ]/g, '’').replace(/\s+/g, ' ').trim(); }

  var ROWS = [], STUDENTS = [], open = {};

  function build(rows) {
    rows.sort(function (a, b) { return a.ts < b.ts ? -1 : a.ts > b.ts ? 1 : 0; });
    var map = {};
    rows.forEach(function (r) {
      var k = norm(r.name);
      var s = map[k] || (map[k] = { key: k, name: r.name, rows: [], devices: {}, ch: {}, last: '' });
      s.name = r.name;
      s.rows.push(r);
      s.devices[r.uid] = 1;
      s.last = r.ts;
      var c = s.ch[r.ch] || (s.ch[r.ch] = { best: 0, n: 0, latest: null });
      c.best = Math.max(c.best, r.pct);
      c.n++;
      c.latest = r;
    });
    return Object.keys(map).map(function (k) {
      var s = map[k];
      var done = CH.filter(function (c) { return s.ch[c]; });
      s.done = done.length;
      s.avg = done.length ? Math.round(done.reduce(function (t, c) { return t + s.ch[c].best; }, 0) / done.length) : null;
      return s;
    });
  }

  function renderTiles() {
    var tests = 0, sum = 0, n = 0;
    STUDENTS.forEach(function (s) { CH.forEach(function (c) { if (s.ch[c]) { tests++; sum += s.ch[c].best; n++; } }); });
    var full = STUDENTS.filter(function (s) { return s.done === CH.length; }).length;
    var week = Date.now() - 7 * 864e5;
    var active = STUDENTS.filter(function (s) { return new Date(s.last).getTime() >= week; }).length;
    var t = [[STUDENTS.length, 'учнів'], [tests, 'пройдених тестів (без повторів)'], [n ? Math.round(sum / n) + '%' : '—', 'середній найкращий результат'],
      [full + ' з ' + STUDENTS.length, 'пройшли всі ' + CH.length + ' тестів'], [active, 'активні за останні 7 днів']];
    $('#tiles').innerHTML = t.map(function (x) { return '<div class="tile"><b>' + esc(x[0]) + '</b><span>' + esc(x[1]) + '</span></div>'; }).join('');
  }

  function renderGrid() {
    var q = norm($('#search').value), sort = $('#sort').value;
    var list = STUDENTS.filter(function (s) { return !q || s.key.indexOf(q) >= 0; });
    list.sort(function (a, b) {
      if (sort === 'avg') return (b.avg === null ? -1 : b.avg) - (a.avg === null ? -1 : a.avg);
      if (sort === 'last') return a.last < b.last ? 1 : -1;
      return a.name.localeCompare(b.name, 'uk');
    });
    var head = '<thead><tr><th>Учень</th>' + CH.map(function (c) {
      return '<th>Розділ ' + c + '<small>' + esc(byCh[c].title) + '</small></th>';
    }).join('') + '<th>Середній</th><th>Остання активність</th></tr></thead>';
    var body = list.map(function (s) {
      var dev = Object.keys(s.devices).length;
      var cells = CH.map(function (c) {
        var x = s.ch[c];
        if (!x) return '<td><span class="cell n">—</span></td>';
        return '<td><span class="cell ' + cls(x.best) + '">' + x.best + '%<small>' + x.n + ' ' + plural(x.n, 'спроба', 'спроби', 'спроб') + '</small></span></td>';
      }).join('');
      var row = '<tr class="st" tabindex="0" data-k="' + esc(s.key) + '" aria-expanded="' + (open[s.key] ? 'true' : 'false') + '"><td>' + esc(s.name) +
        (dev > 1 ? '<small>' + dev + ' пристрої</small>' : '') + '</td>' + cells +
        '<td class="avg">' + (s.avg === null ? '—' : s.avg + '%') + '</td><td>' + esc(fmtDate(s.last)) + '</td></tr>';
      if (open[s.key]) row += '<tr class="det"><td colspan="' + (CH.length + 3) + '">' + details(s) + '</td></tr>';
      return row;
    }).join('');
    $('#grid').innerHTML = head + '<tbody>' + (body || '<tr><td colspan="' + (CH.length + 3) + '">Нікого не знайдено.</td></tr>') + '</tbody>';
  }

  function plural(n, one, few, many) {
    var a = n % 10, b = n % 100;
    return a === 1 && b !== 11 ? one : a >= 2 && a <= 4 && (b < 12 || b > 14) ? few : many;
  }

  function details(s) {
    var rows = s.rows.slice().reverse().map(function (r) {
      var wrong = (r.q || []).map(function (v, i) { return v !== null && v < 1 ? i + 1 : null; }).filter(function (x) { return x; });
      return '<tr><td>' + esc(fmtDate(r.ts, true)) + '</td><td>Розділ ' + esc(r.ch) + '</td><td><b>' + esc(r.pct) + '%</b> (' + esc(r.score) + ' з ' + esc(r.max) + ')</td><td>' + esc(r.attempt) + '</td>' +
        '<td class="miss">' + (wrong.length ? 'Помилки в питаннях: ' + wrong.join(', ') : 'Без помилок') + '</td></tr>';
    }).join('');
    return '<table class="tries"><thead><tr><th>Коли</th><th>Тест</th><th>Результат</th><th>Спроба</th><th></th></tr></thead><tbody>' + rows + '</tbody></table>';
  }

  function renderQuestions() {
    var html = CH.map(function (c) {
      var sum = [], cnt = [];
      STUDENTS.forEach(function (s) {
        var x = s.ch[c];
        if (!x) return;
        (x.latest.q || []).forEach(function (v, i) {
          if (v === null || v === undefined) return;
          sum[i] = (sum[i] || 0) + v; cnt[i] = (cnt[i] || 0) + 1;
        });
      });
      var qs = byCh[c].questions.map(function (qq, i) { return { i: i, text: qq.q, n: cnt[i] || 0, p: cnt[i] ? Math.round(sum[i] / cnt[i] * 100) : null }; })
        .filter(function (x) { return x.p !== null; });
      if (!qs.length) return '';
      qs.sort(function (a, b) { return a.p - b.p || a.i - b.i; });
      var id = 'qall' + c;
      var rows = qs.map(function (x, k) {
        return '<div class="qrow"' + (k >= 5 ? ' data-more="' + id + '" hidden' : '') + '><span class="no">№' + (x.i + 1) + '</span><span>' + esc(x.text) + '</span>' +
          '<span class="qbar ' + cls(x.p) + '"><span class="bar"><i style="width:' + x.p + '%"></i></span><span>' + x.p + '%<br><small>' + x.n + ' уч.</small></span></span></div>';
      }).join('');
      var more = qs.length > 5 ? '<button class="linkish qmore" type="button" data-toggle="' + id + '">Показати всі питання (' + qs.length + ')</button>' : '';
      return '<div class="qch"><h3>Розділ ' + c + '. ' + esc(byCh[c].title) + '</h3>' + rows + more + '</div>';
    }).join('');
    $('#questions').innerHTML = html || '<p class="p-hint">Ще немає даних.</p>';
  }

  $('#questions').addEventListener('click', function (ev) {
    var b = ev.target.closest('[data-toggle]');
    if (!b) return;
    var id = b.getAttribute('data-toggle');
    document.querySelectorAll('[data-more="' + id + '"]').forEach(function (el) { el.hidden = false; });
    b.remove();
  });
  function toggleRow(tr) {
    var k = tr.getAttribute('data-k');
    open[k] = !open[k];
    renderGrid();
  }
  $('#grid').addEventListener('click', function (ev) { var tr = ev.target.closest('tr.st'); if (tr) toggleRow(tr); });
  $('#grid').addEventListener('keydown', function (ev) {
    var tr = ev.target.closest('tr.st');
    if (tr && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); toggleRow(tr); }
  });
  $('#search').addEventListener('input', renderGrid);
  $('#sort').addEventListener('change', renderGrid);

  $('#csvBtn').addEventListener('click', function () {
    var head = ['Час', 'Ім’я', 'Розділ', 'Тест', '%', 'Бали', 'З', 'Спроба', 'Пристрій'];
    var lines = [head].concat(ROWS.map(function (r) {
      return [new Date(r.ts).toLocaleString('uk-UA'), r.name, r.ch, r.title, r.pct, r.score, r.max, r.attempt, r.uid];
    })).map(function (row) {
      return row.map(function (v) { v = String(v); if (/^[=+\-@]/.test(v)) v = '\'' + v; return /[";\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }).join(';');
    });
    var blob = new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'rezultaty-' + new Date().toISOString().slice(0, 10) + '.csv';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  });

  function load() {
    if (!ENDPOINT) return setStatus('Сторінку ще не під’єднано до таблиці результатів.', true);
    if (!KEY) return setStatus('Відкрийте сторінку за посиланням, яке вам надіслали: у ньому є ключ доступу.', true);
    setStatus('Завантаження…');
    fetch(ENDPOINT + '?key=' + encodeURIComponent(KEY))
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (!res.ok) {
          setStatus(res.error === 'denied' ? 'Ключ доступу недійсний. Попросіть нове посилання.' : 'Помилка: ' + res.error, true);
          return;
        }
        ROWS = res.rows;
        STUDENTS = build(ROWS.slice());
        $('#csvBtn').disabled = !ROWS.length;
        $('#studentsCard').hidden = $('#questionsCard').hidden = !ROWS.length;
        setStatus(ROWS.length ? 'Оновлено ' + new Date().toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' }) + '.'
          : 'Поки що ніхто не пройшов тест. Результати з’являться тут, щойно учні почнуть проходити тести.');
        renderTiles();
        if (ROWS.length) { renderGrid(); renderQuestions(); }
      })
      .catch(function () { setStatus('Не вдалося завантажити результати. Перевірте інтернет і натисніть «Оновити».', true); });
  }
  $('#reloadBtn').addEventListener('click', load);
  load();
})();
