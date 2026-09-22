(function () {
  'use strict';
  var root = document.documentElement;
  var store = {
    get: function (k) { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };
  function $(s, el) { return (el || document).querySelector(s); }
  function $$(s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); }
  function h(tag, attrs, kids) {
    var el = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === 'text') el.textContent = attrs[k];
      else if (k === 'html') el.innerHTML = attrs[k];
      else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), attrs[k]);
      else el.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c) el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    return el;
  }
  function shuffle(a) {
    a = a.slice();
    for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; }
    return a;
  }
  function range(n) { var r = []; for (var i = 0; i < n; i++) r.push(i); return r; }

  /* ---------- тема і шрифт ---------- */
  $('#themeBtn').addEventListener('click', function () {
    var dark = root.getAttribute('data-theme') === 'dark' ||
      (!root.getAttribute('data-theme') && matchMedia('(prefers-color-scheme: dark)').matches);
    var next = dark ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('sb-theme', next); } catch (e) {}
  });
  var fs = store.get('sb-fs') || 18;
  function applyFs() { root.style.setProperty('--fs', fs + 'px'); }
  applyFs();
  $('#fsUp').addEventListener('click', function () { fs = Math.min(24, fs + 1); applyFs(); store.set('sb-fs', fs); });
  $('#fsDown').addEventListener('click', function () { fs = Math.max(15, fs - 1); applyFs(); store.set('sb-fs', fs); });

  /* ---------- прогрес читання ---------- */
  var bar = $('.progress span');
  function onScroll() {
    var max = document.documentElement.scrollHeight - innerHeight;
    bar.style.width = (max > 0 ? Math.min(100, scrollY / max * 100) : 0) + '%';
  }
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---------- зміст ---------- */
  var drawer = $('#toc'), scrim = $('#scrim'), tocBtn = $('#tocBtn');
  function toggleToc(open) {
    drawer.classList.toggle('open', open); scrim.classList.toggle('open', open);
    tocBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  tocBtn.addEventListener('click', function () { toggleToc(!drawer.classList.contains('open')); });
  scrim.addEventListener('click', function () { toggleToc(false); });
  $$('#toc a').forEach(function (a) { a.addEventListener('click', function () { if (innerWidth < 1280) toggleToc(false); }); });
  var links = {};
  $$('#toc a').forEach(function (a) { links[a.getAttribute('href').slice(1)] = a; });
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting && links[e.target.id]) {
          $$('#toc a.active').forEach(function (x) { x.classList.remove('active'); });
          links[e.target.id].classList.add('active');
        }
      });
    }, { rootMargin: '-15% 0px -75% 0px' });
    Object.keys(links).forEach(function (id) { var el = document.getElementById(id); if (el) io.observe(el); });
  }

  /* ---------- довгі уривки і режим запам'ятовування ---------- */
  $$('.scripture.long').forEach(function (f) {
    f.classList.add('collapsed');
    var b = $('.more', f);
    b.addEventListener('click', function (ev) {
      ev.stopPropagation();
      var c = f.classList.toggle('collapsed');
      b.textContent = c ? 'Показати весь уривок' : 'Згорнути';
      b.setAttribute('aria-expanded', c ? 'false' : 'true');
    });
  });
  var memoBtn = $('#memoBtn');
  memoBtn.addEventListener('click', function () {
    var on = document.body.classList.toggle('memo');
    memoBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
    $$('.scripture.revealed').forEach(function (f) { f.classList.remove('revealed'); });
  });
  $$('.scripture').forEach(function (f) {
    f.addEventListener('click', function () { if (document.body.classList.contains('memo')) f.classList.toggle('revealed'); });
  });

  /* ---------- тести ---------- */
  var DATA = JSON.parse($('#quiz-data').textContent);
  var LEVELS = ['знання', 'розуміння', 'застосування'];

  function buildQuestion(q, i, data) {
    var box = h('div', { class: 'q', 'data-type': q.type });
    var lvl = h('span', { class: 'lvl' + (q.level === 'застосування' ? ' app' : ''), text: q.level || '' });
    box.appendChild(h('div', { class: 'q-top' }, [h('span', { text: 'Питання ' + (i + 1) }), q.level ? lvl : null]));
    box.appendChild(h('div', { class: 'q-text', text: q.q }));
    var name = 'q' + data.chapter + '_' + i;
    var api = { el: box, q: q };

    if (q.type === 'single' || q.type === 'multi') {
      var order = shuffle(range(q.options.length));
      var inputs = [];
      order.forEach(function (idx) {
        var inp = h('input', { type: q.type === 'single' ? 'radio' : 'checkbox', name: name, value: idx });
        inputs.push(inp);
        box.appendChild(h('label', { class: 'opt' }, [inp, h('span', { text: q.options[idx] })]));
      });
      if (q.type === 'multi') box.appendChild(h('p', { class: 'q-top', text: 'Оберіть усі правильні відповіді' }));
      api.answered = function () { return inputs.some(function (x) { return x.checked; }); };
      api.grade = function () {
        var picked = inputs.filter(function (x) { return x.checked; }).map(function (x) { return +x.value; });
        var right = q.type === 'single' ? [q.answer] : q.answer;
        inputs.forEach(function (x) {
          var v = +x.value, lab = x.parentNode;
          if (right.indexOf(v) >= 0) lab.classList.add('right');
          else if (x.checked) lab.classList.add('wrong');
          x.disabled = true;
        });
        var wrong = picked.filter(function (v) { return right.indexOf(v) < 0; }).length;
        var hit = picked.filter(function (v) { return right.indexOf(v) >= 0; }).length;
        if (!wrong && hit === right.length) return 1;
        if (q.type === 'multi' && !wrong && hit > 0) return 0.5;
        return 0;
      };
    } else if (q.type === 'truefalse') {
      var yes = h('input', { type: 'radio', name: name, value: '1' });
      var no = h('input', { type: 'radio', name: name, value: '0' });
      box.appendChild(h('div', { class: 'tf' }, [
        h('label', { class: 'opt' }, [yes, h('span', { text: 'Так, правильно' })]),
        h('label', { class: 'opt' }, [no, h('span', { text: 'Ні, неправильно' })])
      ]));
      api.answered = function () { return yes.checked || no.checked; };
      api.grade = function () {
        var rightEl = q.answer ? yes : no, wrongEl = q.answer ? no : yes;
        rightEl.parentNode.classList.add('right');
        if (wrongEl.checked) wrongEl.parentNode.classList.add('wrong');
        yes.disabled = no.disabled = true;
        return rightEl.checked ? 1 : 0;
      };
    } else if (q.type === 'match') {
      var rights = shuffle(range(q.pairs.length));
      var sels = q.pairs.map(function (p, k) {
        var sel = h('select', { 'aria-label': p[0] }, [h('option', { value: '', text: '— оберіть —' })]
          .concat(rights.map(function (r) { return h('option', { value: r, text: q.pairs[r][1] }); })));
        box.appendChild(h('div', { class: 'match-row' }, [h('div', { text: p[0] }), sel]));
        return sel;
      });
      box.appendChild(h('p', { class: 'q-top', text: 'Кожен варіант підходить лише до одного пункту' }));
      api.answered = function () { return sels.every(function (s) { return s.value !== ''; }); };
      api.grade = function () {
        var ok = 0;
        sels.forEach(function (s, k) {
          var row = s.parentNode, good = s.value !== '' && +s.value === k;
          row.classList.add(good ? 'right' : 'wrong');
          if (good) ok++; else row.appendChild(h('div', { class: 'fix', text: 'Правильно: ' + q.pairs[k][1] }));
          s.disabled = true;
        });
        return ok / sels.length;
      };
    } else if (q.type === 'order') {
      var cur = shuffle(range(q.items.length));
      while (cur.join() === range(q.items.length).join() && cur.length > 1) cur = shuffle(cur);
      var list = h('ol', { class: 'order-list' });
      var draw = function () {
        list.innerHTML = '';
        cur.forEach(function (idx, pos) {
          var up = h('button', { type: 'button', 'aria-label': 'Вище', text: '↑', onclick: function () { if (pos > 0) { cur.splice(pos - 1, 0, cur.splice(pos, 1)[0]); draw(); } } });
          var dn = h('button', { type: 'button', 'aria-label': 'Нижче', text: '↓', onclick: function () { if (pos < cur.length - 1) { cur.splice(pos + 1, 0, cur.splice(pos, 1)[0]); draw(); } } });
          list.appendChild(h('li', { 'data-i': idx }, [h('span', { text: q.items[idx] }), up, dn]));
        });
      };
      draw();
      box.appendChild(h('p', { class: 'q-top', text: 'Розставте кнопками ↑ ↓' }));
      box.appendChild(list);
      api.answered = function () { return true; };
      api.grade = function () {
        var ok = 0;
        $$('li', list).forEach(function (li, pos) {
          var good = +li.getAttribute('data-i') === pos;
          li.classList.add(good ? 'right' : 'wrong');
          if (good) ok++;
          $$('button', li).forEach(function (b) { b.disabled = true; });
        });
        return ok / cur.length;
      };
      api.correctText = 'Правильний порядок: ' + q.items.join(' → ');
    } else if (q.type === 'reflect') {
      box.classList.add('reflect');
      var ta = h('textarea', { placeholder: 'Запишіть свою відповідь. Її ніхто не побачить – вона лише для вас.' });
      box.appendChild(ta);
      api.answered = function () { return true; };
      api.grade = function () { return null; };
    }

    var fb = h('div', { class: 'fb' });
    box.appendChild(fb);
    api.feedback = function (score) {
      box.classList.add('done');
      if (score === null) {
        box.classList.add('reflect');
        fb.appendChild(h('b', { class: 'st', text: 'Орієнтир' }));
        fb.appendChild(document.createTextNode(q.sample || ''));
        return;
      }
      var st = score === 1 ? 'Правильно' : score === 0 ? 'Неправильно' : 'Частково';
      box.classList.add(score === 1 ? 'ok' : score === 0 ? 'bad' : 'part');
      fb.appendChild(h('b', { class: 'st', text: st }));
      if (api.correctText && score < 1) fb.appendChild(h('div', { text: api.correctText }));
      if (q.explain) fb.appendChild(document.createTextNode(q.explain));
      if (score < 1 && q.anchor && data.sections[q.anchor]) {
        fb.appendChild(h('br'));
        fb.appendChild(h('a', { href: '#' + q.anchor, text: '↩ Перечитати: ' + data.sections[q.anchor] }));
      }
    };
    return api;
  }

  function ringSvg(pct) {
    var r = 46, c = 2 * Math.PI * r, off = c * (1 - pct / 100);
    var col = pct >= 85 ? 'var(--ok)' : pct >= 70 ? 'var(--gold)' : pct >= 50 ? 'var(--part)' : 'var(--bad)';
    return '<svg class="ring" viewBox="0 0 112 112"><circle cx="56" cy="56" r="' + r + '" fill="none" stroke="var(--line)" stroke-width="10"/>' +
      '<circle cx="56" cy="56" r="' + r + '" fill="none" stroke="' + col + '" stroke-width="10" stroke-linecap="round" stroke-dasharray="' + c.toFixed(1) +
      '" stroke-dashoffset="' + off.toFixed(1) + '" transform="rotate(-90 56 56)"/><text x="56" y="63" text-anchor="middle">' + pct + '%</text></svg>';
  }

  function verdict(pct) {
    if (pct >= 85) return ['Матеріал засвоєно глибоко', 'Ви не лише пам’ятаєте зміст, а й умієте застосувати його в конкретних ситуаціях.'];
    if (pct >= 70) return ['Добре, але є прогалини', 'Основне зрозуміло. Перечитайте теми нижче, щоб закрити прогалини.'];
    if (pct >= 50) return ['Знайомство поверхове', 'Частину думок розділу ви впізнаєте, але ще не можете на них спиратися. Перечитайте позначені теми і пройдіть тест ще раз.'];
    return ['Розділ варто прочитати ще раз', 'Поверніться до тексту, особливо до головних думок, і пройдіть тест знову через день-два.'];
  }

  function renderQuiz(app, data) {
    app.innerHTML = '';
    var qs = data.questions.map(function (q, i) { var a = buildQuestion(q, i, data); app.appendChild(a.el); return a; });
    var warn = h('span', { class: 'warn' });
    var resultBox = h('div');
    var checkBtn = h('button', { class: 'btn', type: 'button', text: 'Перевірити відповіді' });
    var retry = h('button', { class: 'btn ghost', type: 'button', text: 'Пройти ще раз', style: 'display:none' });
    var forced = false;
    checkBtn.addEventListener('click', function () {
      var missing = qs.filter(function (a) { return !a.answered(); });
      qs.forEach(function (a) { a.el.classList.toggle('missing', !a.answered()); });
      if (missing.length && !forced) {
        forced = true;
        warn.textContent = 'Без відповіді: ' + missing.length + '. Натисніть ще раз, щоб перевірити як є.';
        missing[0].el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
      warn.textContent = '';
      var total = 0, max = 0, byLvl = {}, review = {};
      qs.forEach(function (a) {
        a.el.classList.remove('missing');
        var s = a.answered() ? a.grade() : (a.grade(), 0);
        if (a.q.type === 'reflect') s = null;
        a.feedback(s);
        if (s === null) return;
        total += s; max += 1;
        var L = a.q.level || 'розуміння';
        byLvl[L] = byLvl[L] || [0, 0]; byLvl[L][0] += s; byLvl[L][1] += 1;
        if (s < 1 && a.q.anchor) review[a.q.anchor] = true;
      });
      var pct = Math.round(total / max * 100);
      var v = verdict(pct);
      var lv = LEVELS.filter(function (L) { return byLvl[L]; }).map(function (L) {
        var p = Math.round(byLvl[L][0] / byLvl[L][1] * 100);
        return '<div class="lvlbar"><span>' + L + '</span><span class="bar"><i style="width:' + p + '%"></i></span><b>' + p + '%</b></div>';
      }).join('');
      var rv = Object.keys(review).filter(function (k) { return data.sections[k]; });
      resultBox.innerHTML = '<div class="result">' + ringSvg(pct) + '<div><h4>' + v[0] + '</h4><p>' + v[1] + '</p><p>Бали: ' +
        (Math.round(total * 10) / 10) + ' з ' + max + '</p></div><div class="levels">' + lv + '</div>' +
        (rv.length ? '<div class="review"><b>Що перечитати:</b><ul>' + rv.map(function (k) { return '<li><a href="#' + k + '">' + data.sections[k] + '</a></li>'; }).join('') + '</ul></div>' : '') +
        '</div>';
      checkBtn.style.display = 'none';
      retry.style.display = '';
      var saved = store.get('sb-results') || {};
      var prev = saved[data.chapter];
      saved[data.chapter] = { pct: pct, best: Math.max(pct, prev ? prev.best || prev.pct : 0), date: new Date().toLocaleDateString('uk-UA'), tries: (prev ? prev.tries || 1 : 0) + 1 };
      store.set('sb-results', saved);
      renderSummary();
      resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
    retry.addEventListener('click', function () { renderQuiz(app, data); app.scrollIntoView({ behavior: 'smooth' }); });
    app.appendChild(h('div', { class: 'quiz-actions' }, [checkBtn, retry, warn]));
    app.appendChild(resultBox);
  }

  function renderSummary() {
    var saved = store.get('sb-results') || {};
    var rows = DATA.map(function (d) {
      var r = saved[d.chapter];
      return '<tr><td>' + d.chapter + '</td><td><a href="#quiz' + d.chapter + '">' + d.title + '</a></td><td>' +
        (r ? r.pct + '%' : '—') + '</td><td>' + (r ? r.best + '%' : '—') + '</td><td class="c-date">' + (r ? r.date : '') + '</td></tr>';
    }).join('');
    var done = DATA.filter(function (d) { return saved[d.chapter]; });
    var avg = done.length ? Math.round(done.reduce(function (s, d) { return s + saved[d.chapter].best; }, 0) / done.length) : null;
    $('#summaryTable').innerHTML = '<div class="table-wrap"><table class="sum-table"><thead><tr><th>№</th><th>Розділ</th><th>Останній</th><th>Найкращий</th><th class="c-date">Дата</th></tr></thead><tbody>' +
      rows + '</tbody></table></div>' + (avg !== null ? '<p style="margin-top:14px">Пройдено тестів: ' + done.length + ' з ' + DATA.length + '. Середній найкращий результат: <b>' + avg + '%</b>.</p>' : '<p style="margin-top:14px">Тести ще не пройдено.</p>');
  }

  DATA.forEach(function (d) {
    var app = $('.quiz-app[data-ch="' + d.chapter + '"]');
    if (app) renderQuiz(app, d);
  });
  renderSummary();
})();
