/**
 * Приймає результати тестів зі сторінки посібника і віддає їх сторінці пастора.
 * Таблиця – та, до якої прив'язаний скрипт. Ключ пастора – PASTOR_KEY у key.gs (не в репозиторії).
 */
var SHEET = 'Результати';
var HEAD = ['Час', 'Ім’я', 'Пристрій', 'Розділ', 'Тест', '%', 'Бали', 'З', 'Спроба', 'Питання', 'ID'];

function sheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  // Інакше дати в клітинках зсуваються на різницю між поясом таблиці і скрипта.
  if (ss.getSpreadsheetTimeZone() !== Session.getScriptTimeZone()) ss.setSpreadsheetTimeZone(Session.getScriptTimeZone());
  var sh = ss.getSheetByName(SHEET);
  if (!sh) {
    sh = ss.insertSheet(SHEET, 0);
    sh.appendRow(HEAD);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, HEAD.length).setFontWeight('bold');
  }
  return sh;
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

function str_(v, max) { return String(v == null ? '' : v).replace(/\s+/g, ' ').trim().slice(0, max); }
function num_(v, lo, hi) { v = Number(v); return isFinite(v) && v >= lo && v <= hi ? v : null; }

function doPost(e) {
  var d;
  try { d = JSON.parse(e.postData.contents); } catch (err) { return json_({ ok: false, error: 'bad_json' }); }
  var name = str_(d.name, 80), uid = str_(d.uid, 40), id = str_(d.id, 40), title = str_(d.title, 200);
  var ch = num_(d.ch, 1, 20), pct = num_(d.pct, 0, 100), score = num_(d.score, 0, 500), max = num_(d.max, 1, 500);
  var attempt = num_(d.attempt, 1, 10000);
  var qs = Array.isArray(d.q) ? d.q.slice(0, 100).map(function (x) { return x === null ? null : num_(x, 0, 1); }) : [];
  if (!name || !id || ch === null || pct === null) return json_({ ok: false, error: 'bad_data' });
  // Формула, що починається з «=», «+», «-», «@», не повинна виконатися в таблиці.
  if (/^[=+\-@]/.test(name)) name = '’' + name;

  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var sh = sheet_();
    var last = sh.getLastRow();
    if (last > 1) {
      var from = Math.max(2, last - 499);
      var ids = sh.getRange(from, HEAD.length, last - from + 1, 1).getValues();
      for (var i = 0; i < ids.length; i++) if (ids[i][0] === id) return json_({ ok: true, dup: true });
    }
    var ts = d.ts ? new Date(d.ts) : new Date();
    if (isNaN(ts.getTime()) || ts > new Date()) ts = new Date();
    sh.appendRow([ts, name, uid, ch, title, pct, score, max, attempt, JSON.stringify(qs), id]);
  } finally {
    lock.releaseLock();
  }
  return json_({ ok: true });
}

function doGet(e) {
  var key = e && e.parameter && e.parameter.key;
  if (!key || typeof PASTOR_KEY === 'undefined' || key !== PASTOR_KEY) return json_({ ok: false, error: 'denied' });
  var sh = sheet_();
  var last = sh.getLastRow();
  var rows = last > 1 ? sh.getRange(2, 1, last - 1, HEAD.length).getValues() : [];
  return json_({
    ok: true,
    rows: rows.map(function (r) {
      var q = [];
      try { q = JSON.parse(r[9] || '[]'); } catch (err) {}
      return {
        ts: r[0] instanceof Date ? r[0].toISOString() : String(r[0]),
        name: String(r[1]).replace(/^’(?=[=+\-@])/, ''), uid: String(r[2]), ch: Number(r[3]), title: String(r[4]),
        pct: Number(r[5]), score: Number(r[6]), max: Number(r[7]), attempt: Number(r[8]), q: q
      };
    })
  });
}

/** Запустити один раз з редактора, щоб надати скрипту доступ до таблиці. */
function setup() {
  sheet_();
}
