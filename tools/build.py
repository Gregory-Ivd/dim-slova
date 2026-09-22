"""Збирає index.html з src/*.md і src/quiz*.json.

Тексти Писання підставляються з кешу bible.com («Біблія. Сучасний переклад», УБТ),
див. fetch.py. Запуск: python tools/build.py
"""
import html
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from refs import parse, remap, UA  # noqa: E402
from fetch import chapter  # noqa: E402

SRC = os.path.join(ROOT, 'src')
ASSETS = os.path.join(ROOT, 'assets')

CHURCH = 'Християнська церква «Перемога»'
CITY = 'м. Рівне'
SCHOOL = 'Біблійна школа «Дім Слова»'
TITLE = 'Слово Боже'
INSTAGRAM = 'https://www.instagram.com/victorychurch_rv/'
FACEBOOK = 'https://www.facebook.com/profile.php?id=100077340400434'

# Синодальне посилання -> як цитувати з УБТ, коли звичайного перерахунку замало.
OVERRIDES = {
    # вірш 89 в УБТ обривається на півфразі й продовжується у 90-му
    'Псалом 118:89': {'extend_to': 90},
    # в оригіналі наведено лише перше речення
    'Осия 4:6': {'first_sentence': True},
}
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5}


def esc(s):
    return html.escape(s, quote=False)


def inline(s):
    s = esc(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    return s


# ---------- Писання ----------

def fmt_ranges(book, pairs):
    """pairs: [(chapter, verse)], suцільні відрізки стискаються: 1:1–3, 14."""
    out, i = [], 0
    last_ch = None
    while i < len(pairs):
        c, v = pairs[i]
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == c and pairs[j + 1][1] == pairs[j][1] + 1:
            j += 1
        seg = f'{v}' if i == j else f'{v}–{pairs[j][1]}'
        out.append(seg if c == last_ch else f'{c}:{seg}')
        last_ch = c
        i = j + 1
    return f'{UA[book]} ' + ', '.join(out)


def scripture(ref):
    book, ch, rng = parse(ref)
    ov = OVERRIDES.get(ref, {})
    syn, cuv = [], []
    for a, b in rng:
        if ov.get('extend_to'):
            b = max(b, ov['extend_to'] - (remap(book, ch, a)[1] - a))
        for v in range(a, b + 1):
            syn.append((ch, v))
            cuv.append(remap(book, ch, v))
    verses = []
    for c, v in cuv:
        vs, _ = chapter(book, c)
        verses.append((c, v, vs[v]))
    if ov.get('first_sentence'):
        c, v, t = verses[0]
        m = re.match(r'(.+?[.!?])\s', t)
        verses = [(c, v, m.group(1) + ' …')]
        cuv = [(c, v)]
        syn = syn[:1]
    label = fmt_ranges(book, cuv)
    syn_label = fmt_ranges(book, syn)
    if book == 'PSA':
        label = label.replace('Псалом', 'Пс.')
        syn_label = syn_label.replace('Псалом', 'Пс.')
    note = ''
    if [c for c, _ in syn] != [c for c, _ in cuv] or [v for _, v in syn] != [v for _, v in cuv]:
        note = f'<span class="syn">у Синодальному перекладі – {esc(syn_label)}</span>'
    parts, prev = [], None
    for c, v, t in verses:
        if prev and not (prev[0] == c and prev[1] + 1 == v):
            parts.append('<span class="gap">…</span> ')
        parts.append(f'<sup>{v}</sup>{esc(t)} ')
        prev = (c, v)
    body = ''.join(parts).strip()
    size = sum(len(t) for _, _, t in verses)
    cls = 'scripture long' if size > 700 else 'scripture'
    return (f'<figure class="{cls}"><blockquote>{body}</blockquote>'
            f'<figcaption><span class="ref">{esc(label)}</span>{note}</figcaption>'
            f'<button class="more" type="button" aria-expanded="false">Показати весь уривок</button>'
            f'</figure>'), size


# ---------- розбір розмітки ----------

def parse_md(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    blocks, para, lst = [], [], None

    def flush():
        nonlocal para, lst
        if para:
            blocks.append({'t': 'p', 'text': ' '.join(para)})
            para = []
        if lst is not None:
            blocks.append({'t': 'ul', 'items': lst})
            lst = None

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        m = re.match(r'^(#{1,3}) (.+?)(?:\s*\{#([\w-]+)\})?$', line)
        if m:
            flush()
            blocks.append({'t': 'h%d' % len(m.group(1)), 'text': m.group(2), 'id': m.group(3)})
            continue
        if line.startswith('(') and blocks and blocks[-1]['t'] == 'h1' and not para:
            blocks[-1]['sub'] = line.strip('()')
            continue
        if line.startswith('@@ '):
            flush()
            blocks.append({'t': 'scr', 'ref': line[3:].strip()})
            continue
        if line.startswith('!! '):
            flush()
            blocks.append({'t': 'key', 'text': line[3:].strip()})
            continue
        if line.startswith('>> '):
            flush()
            blocks.append({'t': 'aside', 'text': line[3:].strip()})
            continue
        if line.startswith('- '):
            if para:
                blocks.append({'t': 'p', 'text': ' '.join(para)})
                para = []
            if lst is None:
                lst = []
            lst.append([line[2:].strip()])
            continue
        if line.startswith('  ') and lst:
            lst[-1].append(line.strip())
            continue
        if lst is not None:
            flush()
        para.append(line.strip())
    flush()
    return blocks


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def merge_keys(blocks):
    """Головна думка, що дослівно є в сусідньому абзаці, підсвічується в ньому самому."""
    out = []
    for i, b in enumerate(blocks):
        if b['t'] != 'key':
            continue
        needle = norm(b['text']).rstrip('.')
        for j in list(range(i - 1, max(-1, i - 4), -1)) + list(range(i + 1, min(len(blocks), i + 3))):
            nb = blocks[j]
            if nb['t'] == 'p' and needle in norm(nb['text']):
                nb.setdefault('marks', []).append(needle)
                b['t'] = 'drop'
                break
            if nb['t'] == 'ul':
                hit = False
                for item in nb['items']:
                    for k, part in enumerate(item):
                        if needle in norm(part):
                            item[k] = part  # позначка ставиться під час рендеру
                            nb.setdefault('marks', []).append(needle)
                            hit = True
                if hit:
                    b['t'] = 'drop'
                    break
            if nb['t'] in ('h1', 'h2'):
                break
    return [b for b in blocks if b['t'] != 'drop']


def apply_marks(text_html, marks):
    for m in marks or []:
        mh = esc(m)
        text_html = text_html.replace(mh, f'<mark class="key">{mh}</mark>', 1)
    return text_html


# ---------- тести ----------

LETTERS = 'АБВГДЕЖЗ'


def quiz_print(q_data, n):
    rnd = random.Random(1000 + n)
    rows = []
    for i, q in enumerate(q_data['questions'], 1):
        t = q['type']
        head = f'<p class="pq-q"><b>{i}.</b> {inline(q["q"])}'
        hint = {'single': 'одна відповідь', 'multi': 'кілька відповідей', 'truefalse': 'так / ні',
                'match': 'відповідність', 'order': 'порядок', 'reflect': 'для роздуму'}[t]
        head += f' <span class="pq-hint">{hint}</span></p>'
        body = ''
        if t in ('single', 'multi'):
            body = '<ol class="pq-opts">' + ''.join(
                f'<li><span class="box"></span><b>{LETTERS[k]})</b> {inline(o)}</li>' for k, o in enumerate(q['options'])) + '</ol>'
        elif t == 'truefalse':
            body = '<p class="pq-tf"><span class="box"></span> Так&nbsp;&nbsp;&nbsp;<span class="box"></span> Ні</p>'
        elif t == 'match':
            right = [p[1] for p in q['pairs']]
            order = list(range(len(right)))
            rnd.shuffle(order)
            q['_print_right'] = order
            body = '<div class="pq-match"><ol>' + ''.join(f'<li>{inline(p[0])} <span class="blank"></span></li>' for p in q['pairs']) + '</ol><ol class="letters">' + ''.join(
                f'<li><b>{LETTERS[k]})</b> {inline(right[idx])}</li>' for k, idx in enumerate(order)) + '</ol></div>'
        elif t == 'order':
            order = list(range(len(q['items'])))
            while order == sorted(order) and len(order) > 1:
                rnd.shuffle(order)
            q['_print_order'] = order
            body = '<ul class="pq-order">' + ''.join(f'<li><span class="blank sm"></span> {inline(q["items"][idx])}</li>' for idx in order) + '</ul>'
        elif t == 'reflect':
            body = '<div class="pq-lines"></div>'
        rows.append(f'<div class="pq">{head}{body}</div>')
    return ''.join(rows)


def answer_key(q_data, n):
    rows = []
    for i, q in enumerate(q_data['questions'], 1):
        t = q['type']
        if t == 'single':
            a = LETTERS[q['answer']]
        elif t == 'multi':
            a = ', '.join(LETTERS[k] for k in q['answer'])
        elif t == 'truefalse':
            a = 'Так' if q['answer'] else 'Ні'
        elif t == 'match':
            order = q['_print_right']
            a = '; '.join(f'{k + 1} – {LETTERS[order.index(k)]}' for k in range(len(q['pairs'])))
        elif t == 'order':
            a = ' → '.join(q['items'])
        else:
            a = None
        if a is None:
            rows.append(f'<li><b class="k-a">Орієнтир:</b> <span class="k-exp">{inline(q.get("sample", ""))}</span></li>')
            continue
        exp = f'<span class="k-exp">{inline(q["explain"])}</span>' if q.get('explain') else ''
        rows.append(f'<li><b class="k-a">{esc(a)}.</b> {exp}</li>')
    return f'<ol class="key-list">{"".join(rows)}</ol>'


# ---------- складання ----------

def render_chapter(n):
    blocks = merge_keys(parse_md(os.path.join(SRC, f'ch{n}.md')))
    quiz = json.load(open(os.path.join(SRC, f'quiz{n}.json'), encoding='utf-8'))
    out, toc, h3n = [], [], 0
    stats = {'verses': 0}
    for b in blocks:
        t = b['t']
        if t == 'h1':
            num, _, title = b['text'].partition('. ')
            sub = f'<p class="ch-sub">{inline(b["sub"])}</p>' if b.get('sub') else ''
            out.append(f'<header class="ch-head" id="{b["id"]}"><span class="ch-num">Розділ {num}</span>'
                       f'<h2>{inline(title)}</h2>{sub}</header>')
            toc.append((b['id'], f'{num}. {title}', []))
        elif t == 'h2':
            title = re.sub(r'^\d+\.\s*', '', b['text'])
            numm = re.match(r'^(\d+)\.', b['text'])
            badge = f'<span class="s-num">{numm.group(1)}</span>' if numm else ''
            out.append(f'<h3 class="sec" id="{b["id"]}">{badge}{inline(title)}</h3>')
            toc[-1][2].append((b['id'], b['text']))
        elif t == 'h3':
            h3n += 1
            out.append(f'<h4 class="sub">{inline(b["text"])}</h4>')
        elif t == 'p':
            out.append(f'<p>{apply_marks(inline(b["text"]), b.get("marks"))}</p>')
        elif t == 'ul':
            items = []
            for item in b['items']:
                first = apply_marks(inline(item[0]), b.get('marks'))
                rest = ''.join(f'<p>{apply_marks(inline(x), b.get("marks"))}</p>' for x in item[1:])
                items.append(f'<li><p class="li-head">{first}</p>{rest}</li>')
            out.append(f'<ul class="points">{"".join(items)}</ul>')
        elif t == 'scr':
            h, size = scripture(b['ref'])
            out.append(h)
            stats['verses'] += 1
        elif t == 'key':
            out.append(f'<aside class="key-idea"><span class="lbl">Головна думка</span><p>{inline(b["text"])}</p></aside>')
        elif t == 'aside':
            out.append(f'<aside class="note"><span class="lbl">Пояснення</span><p>{inline(b["text"])}</p></aside>')
    qjs = {'chapter': n, 'title': quiz['title'], 'questions': quiz['questions'],
           'sections': {sid: re.sub(r'^\d+\.\s*', '', st) for _, _, secs in toc for sid, st in secs}}
    quiz_html = (f'<section class="quiz" id="quiz{n}" data-ch="{n}">'
                 f'<header class="quiz-head"><span class="lbl">Перевір себе · Розділ {n}</span>'
                 f'<h3>{inline(quiz["title"])}</h3>'
                 f'<p class="quiz-intro">{len(quiz["questions"])} питань. Частина з них – життєві ситуації, де треба застосувати прочитане. '
                 f'Після перевірки побачите, які теми варто повторити.</p></header>'
                 f'<div class="quiz-app" data-ch="{n}"></div>'
                 f'<div class="quiz-print">{quiz_print(quiz, n)}</div></section>')
    toc[-1][2].append((f'quiz{n}', 'Перевір себе'))
    return ''.join(out) + quiz_html, toc, qjs, answer_key(quiz, n), quiz['title']


def main():
    chapters, tocs, quizzes, keys = [], [], [], []
    for n in range(1, 6):
        body, toc, qjs, key, qtitle = render_chapter(n)
        chapters.append(f'<article class="chapter" data-ch="{n}">{body}</article>')
        tocs += toc
        quizzes.append(qjs)
        keys.append((n, qtitle, key))

    epi_vs, _ = chapter('2TI', 2)
    epigraph = epi_vs[15]
    prayer_vs, _ = chapter('PSA', 119)
    prayer = prayer_vs[18]

    toc_html = ''.join(
        f'<li><a href="#{cid}">{esc(ct)}</a><ol>' + ''.join(f'<li><a href="#{sid}">{esc(st)}</a></li>' for sid, st in secs) + '</ol></li>'
        for cid, ct, secs in tocs)
    keys_html = ''.join(f'<section class="key-ch"><h3>Розділ {n}. {esc(t)}</h3>{k}</section>' for n, t, k in keys)

    tpl = open(os.path.join(ASSETS, 'template.html'), encoding='utf-8').read()
    css = open(os.path.join(ASSETS, 'style.css'), encoding='utf-8').read()
    js = open(os.path.join(ASSETS, 'app.js'), encoding='utf-8').read()
    preface = open(os.path.join(SRC, 'preface.html'), encoding='utf-8').read()
    page = (tpl.replace('{{CSS}}', css).replace('{{JS}}', js)
            .replace('{{PREFACE}}', preface)
            .replace('{{EPIGRAPH}}', esc(epigraph)).replace('{{PRAYER}}', esc(prayer))
            .replace('{{TOC}}', toc_html).replace('{{CHAPTERS}}', ''.join(chapters))
            .replace('{{KEYS}}', keys_html)
            .replace('{{QUIZ_DATA}}', json.dumps(quizzes, ensure_ascii=False).replace('</', '<\\/'))
            .replace('{{CHURCH}}', CHURCH).replace('{{CITY}}', CITY).replace('{{SCHOOL}}', SCHOOL)
            .replace('{{TITLE}}', TITLE).replace('{{INSTAGRAM}}', INSTAGRAM).replace('{{FACEBOOK}}', FACEBOOK))
    left = re.findall(r'\{\{[A-Z_]+\}\}', page)
    assert not left, left
    open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(page)
    print('index.html', len(page), 'bytes')


if __name__ == '__main__':
    main()
