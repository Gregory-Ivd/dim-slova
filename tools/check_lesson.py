"""Перевірка уроку перед публікацією: python tools/check_lesson.py <slug> [<slug> …]

- lesson.json заповнено, урок є в src/lessons.json;
- усі посилання @@ знаходяться в перекладі УБТ;
- тести відповідають tools/SPEC.md: типи, рівень «застосування», пояснення, якорі, індекси відповідей,
  правильні відповіді single на різних позиціях, жодного TODO;
- розділи збираються без помилок.
Код виходу 1, якщо є помилки.
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
os.chdir(ROOT)
import build  # noqa: E402

MIN = {'single': 5, 'multi': 2, 'truefalse': 2, 'match': 1, 'order': 1, 'reflect': 1}


def check(slug):
    errs, warns = [], []
    ldir = os.path.join('src', slug)
    cfg = json.load(open(os.path.join(ldir, 'lesson.json'), encoding='utf-8'))
    build.NUMBERING = cfg.get('numbering', 'ubt')
    for k in ('title', 'pdf', 'meta', 'summary', 'epigraph', 'prayer'):
        if not cfg.get(k) or 'TODO' in json.dumps(cfg.get(k), ensure_ascii=False):
            errs.append(f'lesson.json: {k} не заповнено')
    if slug not in [e['slug'] for e in json.load(open('src/lessons.json', encoding='utf-8'))]:
        errs.append('уроку немає в src/lessons.json')
    for key in ('epigraph', 'prayer'):
        try:
            build.verse(cfg[key])
        except Exception as e:
            errs.append(f'lesson.json: {key} {cfg.get(key)} не знайдено ({e})')
    n, refs = 1, 0
    while os.path.exists(os.path.join(ldir, f'ch{n}.md')):
        md = open(os.path.join(ldir, f'ch{n}.md'), encoding='utf-8').read()
        ids = set(re.findall(r'\{#([\w-]+)\}', md))
        for ref in re.findall(r'^@@ (.+)$', md, re.M):
            refs += 1
            try:
                build.scripture(ref.strip())
            except Exception as e:
                errs.append(f'ch{n}.md: посилання «{ref}» не знайдено ({type(e).__name__}: {e})')
        qpath = os.path.join(ldir, f'quiz{n}.json')
        if not os.path.exists(qpath):
            errs.append(f'немає quiz{n}.json')
            n += 1
            continue
        raw = open(qpath, encoding='utf-8').read()
        quiz = json.loads(raw)
        qs = quiz['questions']
        if 'TODO' in json.dumps(qs, ensure_ascii=False):
            errs.append(f'quiz{n}.json: є незаповнені TODO')
        types = collections.Counter(q['type'] for q in qs)
        for t, m in MIN.items():
            if types[t] < m:
                errs.append(f'quiz{n}.json: {t} – {types[t]}, треба ≥{m}')
        if not 14 <= len(qs) <= 18:
            warns.append(f'quiz{n}.json: {len(qs)} питань (рекомендовано 14–18)')
        if sum(q.get('level') == 'застосування' for q in qs) < 5:
            errs.append(f'quiz{n}.json: менше 5 питань рівня «застосування»')
        for q in qs:
            qid = q.get('id', '?')
            if q['type'] != 'reflect' and not q.get('explain'):
                errs.append(f'quiz{n}.json {qid}: немає explain')
            if q.get('anchor') and q['anchor'] not in ids:
                errs.append(f'quiz{n}.json {qid}: якоря {q["anchor"]} немає в ch{n}.md')
            if q['type'] == 'single' and not 0 <= q['answer'] < len(q['options']):
                errs.append(f'quiz{n}.json {qid}: answer поза варіантами')
            if q['type'] == 'multi' and (not q['answer'] or any(not 0 <= a < len(q['options']) for a in q['answer'])):
                errs.append(f'quiz{n}.json {qid}: answer поза варіантами')
        pos = collections.Counter(q['answer'] for q in qs if q['type'] == 'single')
        if pos and max(pos.values()) > (sum(pos.values()) + 1) // 2:
            warns.append(f'quiz{n}.json: правильні відповіді single здебільшого на позиції {pos.most_common(1)[0][0]} – перемішайте')
        try:
            build.render_chapter(ldir, n)
        except Exception as e:
            errs.append(f'ch{n}: не збирається ({type(e).__name__}: {e})')
        n += 1
    if n == 1:
        errs.append('немає жодного chN.md')
    print(f'{slug}: розділів {n - 1}, посилань {refs}')
    for w in warns:
        print('  увага:', w)
    for e in errs:
        print('  ПОМИЛКА:', e)
    return not errs


if __name__ == '__main__':
    slugs = sys.argv[1:] or [e['slug'] for e in json.load(open(os.path.join(ROOT, 'src', 'lessons.json'), encoding='utf-8'))]
    ok = all([check(s) for s in slugs])
    print('OK' if ok else 'Є помилки')
    sys.exit(0 if ok else 1)
