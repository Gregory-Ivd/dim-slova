"""Заготовка нового уроку з PDF-конспекту (оригіналу з обкладинкою).

python tools/new_lesson.py <конспект.pdf> [--slug vira] [--chapters 4] [--force]

Створює src/<slug>/: lesson.json, preface.html, ch1.md … chN.md (текст конспекту в розмітці уроку,
теми згруповано в розділи приблизно однакового розміру), quiz1.json … quizN.json – ШАБЛОНИ тестів,
які треба заповнити (див. tools/SPEC.md), і додає урок у src/lessons.json.
Далі: заповнити тести, перевірити `python tools/check_lesson.py <slug>`, зібрати й опублікувати
(README, розділ «Новий урок»).
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'src')
sys.path.insert(0, HERE)
import konspekt  # noqa: E402
from refs import parse as parse_ref, UA_BOOKS  # noqa: E402

ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII']
TRANSLIT = dict(zip('абвгґдежзиіїйклмнопрстуфхцчшщьюяє’\'',
                    ['a', 'b', 'v', 'h', 'g', 'd', 'e', 'zh', 'z', 'y', 'i', 'i', 'i', 'k', 'l', 'm', 'n', 'o', 'p', 'r',
                     's', 't', 'u', 'f', 'kh', 'ts', 'ch', 'sh', 'shch', '', 'iu', 'ia', 'ie', '', '']))


def slugify(title):
    s = ''.join(TRANSLIT.get(c, c) for c in title.lower())
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def size(sec):
    return len(sec['intro']) + sum(len(p['text']) + len(p['lead']) for p in sec['points'])


def partition(sections, n):
    """Суцільні групи тем, щоб найбільший розділ був якомога меншим."""
    sizes = [size(s) for s in sections]
    best = None

    def go(i, k, groups):
        nonlocal best
        if k == 1:
            g = groups + [list(range(i, len(sizes)))]
            worst = max(sum(sizes[j] for j in grp) for grp in g)
            if best is None or worst < best[0]:
                best = (worst, g)
            return
        for j in range(i + 1, len(sizes) - k + 2):
            go(j, k - 1, groups + [list(range(i, j))])
    go(0, n, [])
    return [[sections[j] for j in grp] for grp in best[1]]


def point_md(p, n):
    lead = p['lead'].rstrip(' .:')
    out = [f'### {n}. {lead}', ''] if lead else []
    if p['text']:
        out.append(p['text'])
    return out


def section_md(sec, sid):
    out = [f'## {sec["title"]} {{#{sid}}}', '']
    if sec['intro']:
        out += [sec['intro'], '']
    keys = {k['after']: k['text'] for k in sec['keys']}
    n, pending_refs, in_list = 0, [], False

    def refs_out():
        nonlocal pending_refs
        lines = [f'@@ {r}' for r in pending_refs]
        pending_refs = []
        return lines + [''] if lines else []

    for i, p in enumerate(sec['points']):
        if p['level'] == 1:
            if in_list:
                out.append('')
                in_list = False
            out += refs_out()
            n += 1
            out += point_md(p, n) + ['']
        else:
            lead = p['lead'].rstrip(' ')
            out.append(f'- **{lead}** {p["text"]}'.rstrip() if lead else f'- {p["text"]}')
            in_list = True
        pending_refs += p['refs']
        if i + 1 in keys:
            if in_list:
                out.append('')
                in_list = False
            out += refs_out()
            out += [f'!! {keys[i + 1]}', '']
    if in_list:
        out.append('')
    out += refs_out()
    if 0 in keys and not sec['points']:
        out += [f'!! {keys[0]}', '']
    return out


QUIZ_TEMPLATE = [
    ('single', 'знання'), ('single', 'розуміння'), ('single', 'застосування'), ('single', 'застосування'),
    ('single', 'розуміння'), ('single', 'застосування'), ('single', 'знання'), ('single', 'застосування'),
    ('multi', 'знання'), ('multi', 'розуміння'), ('truefalse', 'знання'), ('truefalse', 'розуміння'),
    ('match', 'розуміння'), ('order', 'розуміння'), ('reflect', 'застосування'),
]


def quiz_template(n, title, anchors, ideas):
    qs = []
    for i, (t, lvl) in enumerate(QUIZ_TEMPLATE, 1):
        q = {'id': f'q{n}-{i:02d}', 'type': t, 'level': lvl, 'q': 'TODO', 'anchor': anchors[(i - 1) % len(anchors)]}
        if t in ('single', 'multi'):
            # правильний варіант single – на різних позиціях (у PDF і ключі порядок видно)
            q.update(options=['TODO', 'TODO', 'TODO', 'TODO'], answer=[0, 2] if t == 'multi' else [2, 0, 3, 1][(i + n) % 4])
        elif t == 'truefalse':
            q['answer'] = True
        elif t == 'match':
            q['pairs'] = [['TODO', 'TODO'], ['TODO', 'TODO'], ['TODO', 'TODO']]
        elif t == 'order':
            q['items'] = ['TODO', 'TODO', 'TODO']
        if t == 'reflect':
            q['sample'] = 'TODO'
            del q['anchor']
        else:
            q['explain'] = 'TODO'
        qs.append(q)
    data = {'chapter': n, 'title': title, 'questions': qs}
    if ideas:
        data['_konspekt_questions'] = ideas  # «Перевір себе» з конспекту – ідеї для питань; збирач їх ігнорує
    return data


PREFACE = '''<section class="preface" id="preface">
  <span class="lbl">Передмова</span>
  <figure class="epigraph">
    <blockquote>{{EPIGRAPH}}</blockquote>
    <figcaption>{{EPIGRAPH_REF}}</figcaption>
  </figure>

  <p class="lead">Це урок %(no)d Біблійної школи «Дім Слова»%(prev)s. Його тема – «%(title)s»: %(topics)s.</p>

  <p>Кожну думку тут підкріплено місцями Писання – прочитайте їх уважно, бо саме Слово Боже, а не пояснення до нього, змінює життя.</p>

  <p>Кожен розділ завершується тестом. Він перевіряє, чи зрозуміла прочитане людина, і тому частина питань описує ситуації з життя, де його треба застосувати. Відповіді з поясненнями зібрано наприкінці посібника, а на вебсторінці тест перевіряється одразу і показує, які теми варто перечитати.</p>

  <figure class="prayer">
    <span class="lbl">Перед кожним заняттям</span>
    <blockquote>{{PRAYER}}</blockquote>
    <figcaption>{{PRAYER_REF}}</figcaption>
  </figure>

  <div class="legend">
    <h3>Як читати посібник</h3>
    <div class="legend-grid">
      <div class="lg lg-scr"><b>Святе Письмо</b><span>Біблійні тексти виділено золотою рамкою. Посилання стоїть під текстом.</span></div>
      <div class="lg lg-key"><b>Головна думка</b><span>Висновок, який варто запам’ятати. У тексті такі речення підсвічено.</span></div>
      <div class="lg lg-note"><b>Пояснення</b><span>Значення слова, історичний фон, приклад.</span></div>
      <div class="lg lg-quiz"><b>Перевір себе</b><span>Тест наприкінці розділу: знання, розуміння, застосування.</span></div>
    </div>
  </div>

  <p class="source-note">Українською перекладено та оформлено за навчальним матеріалом Біблійної школи «Робітники Царства» християнської церкви «Перемога» (м. Київ). Використано з дозволу.<br>Цитати Святого Письма наведено за виданням «Біблія. Сучасний переклад» © Українське Біблійне Товариство, 2020–2023. Посилання подано за нумерацією цього перекладу.</p>
</section>
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pdf')
    ap.add_argument('--slug')
    ap.add_argument('--chapters', type=int, help='кількість розділів (типово – за обсягом, 3–5)')
    ap.add_argument('--force', action='store_true', help='перезаписати наявну теку уроку')
    a = ap.parse_args()

    k = konspekt.parse(a.pdf)
    title, secs = k['title'], k['sections']
    slug = a.slug or slugify(title)
    ldir = os.path.join(SRC, slug)
    if os.path.exists(ldir) and not a.force:
        sys.exit(f'{ldir} вже існує (--force, щоб перезаписати)')
    os.makedirs(ldir, exist_ok=True)

    total = sum(size(s) for s in secs)
    n = a.chapters or max(3, min(5, round(total / 2000)))  # ~2000 знаків конспекту на розділ, як у «Вірі»
    n = min(n, len(secs))
    groups = partition(secs, n)

    refs, unknown = [], set()
    for ci, grp in enumerate(groups, 1):
        ch_title = ' · '.join(s['title'] for s in grp)
        md = [f'# {ROMAN[ci - 1]}. {ch_title} {{#ch{ci}}}', '']
        anchors = []
        for si, sec in enumerate(grp, 1):
            sid = f'ch{ci}-s{si}'
            anchors.append(sid)
            md += section_md(sec, sid)
            for p in sec['points']:
                for r in p['refs']:
                    refs.append(r)
                    try:
                        parse_ref(r)
                    except Exception:
                        unknown.add(r)
        text = re.sub(r'\n{3,}', '\n\n', '\n'.join(md)).strip() + '\n'
        open(os.path.join(ldir, f'ch{ci}.md'), 'w', encoding='utf-8').write(text)
        quiz = quiz_template(ci, ch_title, anchors, k['questions'] if ci == 1 else None)
        open(os.path.join(ldir, f'quiz{ci}.json'), 'w', encoding='utf-8').write(json.dumps(quiz, ensure_ascii=False, indent=1) + '\n')

    lessons_path = os.path.join(SRC, 'lessons.json')
    lessons = json.load(open(lessons_path, encoding='utf-8'))
    if not any(e['slug'] == slug for e in lessons):
        lessons.append({'slug': slug, 'label': f'Урок {len(lessons)}'})
        json.dump(lessons, open(lessons_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    idx = [e['slug'] for e in lessons].index(slug)
    prev = lessons[idx - 1]['slug'] if idx > 0 else None
    prev_title = json.load(open(os.path.join(SRC, prev, 'lesson.json'), encoding='utf-8'))['title'] if prev else None

    # Епіграф – перший вірш, на який посилається конспект (замініть, якщо є кращий).
    epi = ['PSA', 119, 105]
    for r in refs:
        try:
            book, c, rng = parse_ref(r)
        except Exception:
            continue
        epi = [book, c, rng[0][0]]
        break
    topics = k['meta'].replace(' · ', ', ').lower() if k['meta'] else title.lower()
    cfg = {'title': title, 'pdf': f'{slug}.pdf', 'meta': k['meta'],
           'summary': 'TODO: одне речення для картки уроку на головній сторінці.',
           'epigraph': epi, 'prayer': ['PSA', 119, 18], 'numbering': 'ubt'}
    json.dump(cfg, open(os.path.join(ldir, 'lesson.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    no = idx  # «Вступ» має індекс 0
    prev_txt = f' після уроку «{prev_title}»' if prev_title and idx > 1 else ''
    open(os.path.join(ldir, 'preface.html'), 'w', encoding='utf-8').write(
        PREFACE % {'no': no, 'prev': prev_txt, 'title': title, 'topics': topics})

    print(f'src/{slug}/ – «{title}», {lessons[idx]["label"]}')
    for ci, grp in enumerate(groups, 1):
        print(f'  розділ {ci}: ' + ' · '.join(s['title'] for s in grp) + f'  ({sum(size(s) for s in grp)} знаків)')
    print(f'  посилань: {len(refs)}; питань «Перевір себе»: {len(k["questions"])} (у quiz1.json → _konspekt_questions)')
    if unknown:
        print('  НЕВІДОМІ КНИГИ (додати в tools/refs.py, UA):', ', '.join(sorted(unknown)))
    print('Далі: перевірити розділи і назви, заповнити TODO в quiz*.json і lesson.json → python tools/check_lesson.py ' + slug)


if __name__ == '__main__':
    main()
