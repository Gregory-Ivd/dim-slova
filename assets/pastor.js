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
  var LESSONS = JSON.parse(qd.textContent);
  var bySlug = {};
  LESSONS.forEach(function (L) { bySlug[L.slug] = L; });

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
  function plural(n, one, few, many) {
    var a = n % 10, b = n % 100;
    return a === 1 && b !== 11 ? one : a >= 2 && a <= 4 && (b < 12 || b > 14) ? few : many;
  }

  /* ---------- вибір уроку ---------- */
  var sel = $('#lesson');
  sel.innerHTML = '<option value="all">Усі уроки – огляд</option>' + LESSONS.map(function (L) {
    return '<option value="' + esc(L.slug) + '">' + esc(L.label + ' · ' + L.title) + '</option>';
  }).join('');
  var cur = ls('sb-plesson');
  if (!cur || (cur !== 'all' && !bySlug[cur])) cur = 'all';
  sel.value = cur;
  sel.addEventListener('change', function () { cur = sel.value; ls('sb-plesson', cur); open = {}; render(); });

  var ROWS = [], open = {};

  // Учні з найкращими результатами по кожному тесту кожного уроку.
  function students(rows) {
    rows = rows.slice().sort(function (a, b) { return a.ts < b.ts ? -1 : a.ts > b.ts ? 1 : 0; });
    var map = {};
    rows.forEach(function (r) {
      if (!bySlug[r.lesson]) return;
      var k = norm(r.name);
      var s = map[k] || (map[k] = { key: k, name: r.name, rows: [], devices: {}, t: {}, last: '' });
      s.name = r.name;
      s.rows.push(r);
      s.devices[r.uid] = 1;
      s.last = r.ts;
      var tk = r.lesson + '/' + r.ch;
      var t = s.t[tk] || (s.t[tk] = { best: 0, n: 0, latest: null });
      t.best = Math.max(t.best, r.pct);
      t.n++;
      t.latest = r;
    });
    return Object.keys(map).map(function (k) { return map[k]; });
  }

  // Стовпці таблиці: розділи уроку або уроки в огляді.
  function columns() {
    if (cur !== 'all') {
      return bySlug[cur].chapters.map(function (c) {
        return {
          head: 'Розділ ' + c.chapter, sub: c.title,
          cell: function (s) { var t = s.t[cur + '/' + c.chapter]; return t ? { pct: t.best, note: t.n + ' ' + plural(t.n, 'спроба', 'спроби', 'спроб') } : null; }
        };
      });
    }
    return LESSONS.map(function (L) {
      return {
        head: L.label, sub: L.title,
        cell: function (s) {
          var done = L.chapters.filter(function (c) { return s.t[L.slug + '/' + c.chapter]; });
          if (!done.length) return null;
          var avg = Math.round(done.reduce(function (a, c) { return a + s.t[L.slug + '/' + c.chapter].best; }, 0) / done.length);
          return { pct: avg, note: done.length + ' з ' + L.chapters.length + ' тестів' };
        }
      };
    });
  }

  function view() {
    var cols = columns();
    var list = students(ROWS).map(function (s) {
      var cells = cols.map(function (c) { return c.cell(s); });
      var vals = cells.filter(Boolean);
      s.cells = cells;
      s.done = vals.length;
      s.avg = vals.length ? Math.round(vals.reduce(function (a, v) { return a + v.pct; }, 0) / vals.length) : null;
      return s;
    }).filter(function (s) { return cur === 'all' || s.done; });
    return { cols: cols, list: list };
  }

  function renderTiles(v) {
    var tests = 0, sum = 0;
    v.list.forEach(function (s) { s.cells.forEach(function (c) { if (c) { tests++; sum += c.pct; } }); });
    var full = v.list.filter(function (s) { return s.done === v.cols.length; }).length;
    var week = Date.now() - 7 * 864e5;
    var active = v.list.filter(function (s) { return new Date(s.last).getTime() >= week; }).length;
    var all = cur === 'all';
    var t = [[v.list.length, plural(v.list.length, 'учень', 'учні', 'учнів')],
      [tests, all ? 'уроків розпочато' : 'пройдених тестів (без повторів)'],
      [tests ? Math.round(sum / tests) + '%' : '—', 'середній найкращий результат'],
      [full + ' з ' + v.list.length, all ? 'пройшли всі ' + v.cols.length + ' ' + plural(v.cols.length, 'урок', 'уроки', 'уроків') : 'пройшли всі ' + v.cols.length + ' тестів'],
      [active, 'активні за останні 7 днів']];
    $('#tiles').innerHTML = t.map(function (x) { return '<div class="tile"><b>' + esc(x[0]) + '</b><span>' + esc(x[1]) + '</span></div>'; }).join('');
  }

  function renderGrid(v) {
    var q = norm($('#search').value), sort = $('#sort').value;
    var list = v.list.filter(function (s) { return !q || s.key.indexOf(q) >= 0; });
    list.sort(function (a, b) {
      if (sort === 'avg') return (b.avg === null ? -1 : b.avg) - (a.avg === null ? -1 : a.avg);
      if (sort === 'last') return a.last < b.last ? 1 : -1;
      return a.name.localeCompare(b.name, 'uk');
    });
    var span = v.cols.length + 3;
    var head = '<thead><tr><th>Учень</th>' + v.cols.map(function (c) {
      return '<th>' + esc(c.head) + '<small>' + esc(c.sub) + '</small></th>';
    }).join('') + '<th>Середній</th><th>Остання активність</th></tr></thead>';
    var body = list.map(function (s) {
      var dev = Object.keys(s.devices).length;
      var cells = s.cells.map(function (x) {
        if (!x) return '<td><span class="cell n">—</span></td>';
        return '<td><span class="cell ' + cls(x.pct) + '">' + x.pct + '%<small>' + esc(x.note) + '</small></span></td>';
      }).join('');
      var row = '<tr class="st" tabindex="0" data-k="' + esc(s.key) + '" aria-expanded="' + (open[s.key] ? 'true' : 'false') + '"><td>' + esc(s.name) +
        (dev > 1 ? '<small>' + dev + ' пристрої</small>' : '') + '</td>' + cells +
        '<td class="avg">' + (s.avg === null ? '—' : s.avg + '%') + '</td><td>' + esc(fmtDate(s.last)) + '</td></tr>';
      if (open[s.key]) row += '<tr class="det"><td colspan="' + span + '">' + details(s) + '</td></tr>';
      return row;
    }).join('');
    $('#grid').innerHTML = head + '<tbody>' + (body || '<tr><td colspan="' + span + '">Нікого не знайдено.</td></tr>') + '</tbody>';
  }

  function details(s) {
    var rows = s.rows.filter(function (r) { return cur === 'all' || r.lesson === cur; }).reverse().map(function (r) {
      var wrong = (r.q || []).map(function (v, i) { return v !== null && v < 1 ? i + 1 : null; }).filter(function (x) { return x; });
      var L = bySlug[r.lesson];
      return '<tr><td>' + esc(fmtDate(r.ts, true)) + '</td><td>' + (cur === 'all' ? esc(L.title) + ', р' : 'Р') + 'озділ ' + esc(r.ch) + '</td><td><b>' + esc(r.pct) + '%</b> (' + esc(r.score) + ' з ' + esc(r.max) + ')</td><td>' + esc(r.attempt) + '</td>' +
        '<td class="miss">' + (wrong.length ? 'Помилки в питаннях: ' + wrong.join(', ') : 'Без помилок') + '</td></tr>';
    }).join('');
    return '<table class="tries"><thead><tr><th>Коли</th><th>Тест</th><th>Результат</th><th>Спроба</th><th></th></tr></thead><tbody>' + rows + '</tbody></table>';
  }

  function renderQuestions(v) {
    var L = bySlug[cur];
    var html = L.chapters.map(function (c) {
      var sum = [], cnt = [];
      v.list.forEach(function (s) {
        var t = s.t[cur + '/' + c.chapter];
        if (!t) return;
        (t.latest.q || []).forEach(function (x, i) {
          if (x === null || x === undefined) return;
          sum[i] = (sum[i] || 0) + x; cnt[i] = (cnt[i] || 0) + 1;
        });
      });
      var qs = c.questions.map(function (qq, i) { return { i: i, text: qq.q, n: cnt[i] || 0, p: cnt[i] ? Math.round(sum[i] / cnt[i] * 100) : null }; })
        .filter(function (x) { return x.p !== null; });
      if (!qs.length) return '';
      qs.sort(function (a, b) { return a.p - b.p || a.i - b.i; });
      var id = 'qall' + c.chapter;
      var rows = qs.map(function (x, k) {
        return '<div class="qrow"' + (k >= 5 ? ' data-more="' + id + '" hidden' : '') + '><span class="no">№' + (x.i + 1) + '</span><span>' + esc(x.text) + '</span>' +
          '<span class="qbar ' + cls(x.p) + '"><span class="bar"><i style="width:' + x.p + '%"></i></span><span>' + x.p + '%<br><small>' + x.n + ' уч.</small></span></span></div>';
      }).join('');
      var more = qs.length > 5 ? '<button class="linkish qmore" type="button" data-toggle="' + id + '">Показати всі питання (' + qs.length + ')</button>' : '';
      return '<div class="qch"><h3>Розділ ' + c.chapter + '. ' + esc(c.title) + '</h3>' + rows + more + '</div>';
    }).join('');
    $('#questions').innerHTML = html || '<p class="p-hint">Ще немає даних.</p>';
  }

  function render() {
    var v = view();
    $('#gridHint').textContent = cur === 'all'
      ? 'Число – середній найкращий результат тестів уроку, під ним – скільки тестів пройдено. Натисніть на учня, щоб побачити всі спроби.'
      : 'Число – найкращий результат тесту, під ним – кількість спроб. Натисніть на учня, щоб побачити всі спроби.';
    renderTiles(v);
    $('#studentsCard').hidden = !v.list.length;
    $('#questionsCard').hidden = cur === 'all' || !v.list.length;
    $('#empty').hidden = !!v.list.length || !ROWS.length;
    if (!v.list.length) return;
    renderGrid(v);
    if (cur !== 'all') renderQuestions(v);
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
    renderGrid(view());
  }
  $('#grid').addEventListener('click', function (ev) { var tr = ev.target.closest('tr.st'); if (tr) toggleRow(tr); });
  $('#grid').addEventListener('keydown', function (ev) {
    var tr = ev.target.closest('tr.st');
    if (tr && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); toggleRow(tr); }
  });
  $('#search').addEventListener('input', function () { renderGrid(view()); });
  $('#sort').addEventListener('change', function () { renderGrid(view()); });

  $('#csvBtn').addEventListener('click', function () {
    var head = ['Час', 'Ім’я', 'Урок', 'Розділ', 'Тест', '%', 'Бали', 'З', 'Спроба', 'Пристрій'];
    var lines = [head].concat(ROWS.map(function (r) {
      var L = bySlug[r.lesson];
      return [new Date(r.ts).toLocaleString('uk-UA'), r.name, L ? L.title : r.lesson, r.ch, r.title, r.pct, r.score, r.max, r.attempt, r.uid];
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
        ROWS = res.rows.map(function (r) { r.lesson = r.lesson || 'slovo-bozhe'; return r; });
        $('#csvBtn').disabled = !ROWS.length;
        $('#lessonBar').hidden = false;
        setStatus(ROWS.length ? 'Оновлено ' + new Date().toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' }) + '.'
          : 'Поки що ніхто не пройшов тест. Результати з’являться тут, щойно учні почнуть проходити тести.');
        render();
      })
      .catch(function () { setStatus('Не вдалося завантажити результати. Перевірте інтернет і натисніть «Оновити».', true); });
  }
  $('#reloadBtn').addEventListener('click', load);
  load();
})();
