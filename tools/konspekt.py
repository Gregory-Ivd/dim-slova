"""Читає PDF-конспект теми (оригінал з обкладинкою) за шрифтами верстки.

Сторінка 1 – обкладинка: назва (найбільший рядок) і перелік тем (рядок під «Конспект теми»).
Далі: тема – Cormorant ~16 pt («I. Назва»); пункт – золотий номер + жирний початок (рівень за відступом);
посилання – після «▸», дрібний шрифт; головна думка – курсив; «Перевір себе» – питання наприкінці.
"""
import re
import pymupdf

FOOTER_Y = 795          # нижче – колонтитул
REF_COLOR = 0x7a5a1a    # колір посилань
NUM_COLOR = 0xb0852b    # золоті номери пунктів
LEVEL2_X = 58           # пункт другого рівня починається правіше


def _lines(page):
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            spans = [s for s in l['spans'] if s['text']]
            if spans and l['bbox'][1] < FOOTER_Y:
                yield l['bbox'], spans


def cover(doc):
    spans = [s for b in doc[0].get_text('dict')['blocks'] for l in b.get('lines', []) for s in l['spans'] if s['text'].strip()]
    big = max(s['size'] for s in spans)
    title = ' '.join(s['text'].strip() for s in spans if s['size'] >= big - 0.5)
    text = re.sub(r'\s+', ' ', ' '.join(s['text'] for s in spans))
    m = re.search(r'Конспект теми\s*(.+?)\s*INSTAGRAM', text, re.I)
    meta = m.group(1).strip() if m else ''
    return title, meta


def _span_md(s):
    t = s['text']
    if 'Bold' in s['font'] and s['color'] != 0x1f3a5f and t.strip():
        lead = len(t) - len(t.lstrip())
        trail = len(t) - len(t.rstrip())
        return t[:lead] + '**' + t.strip() + '**' + t[len(t) - trail:]
    return t


def parse(path):
    """-> dict(title, meta, sections=[{title, intro, points, keys}], questions=[...])"""
    doc = pymupdf.open(path)
    title, meta = cover(doc)
    sections, questions = [], []
    cur = None          # поточна тема
    pt = None           # поточний пункт
    mode = 'text'       # text | refs | check
    key_buf = []

    def flush_key():
        if key_buf and cur is not None:
            cur['keys'].append({'after': len(cur['points']), 'text': ' '.join(key_buf).strip()})
        key_buf.clear()

    for page in doc.pages(1):
        for bbox, spans in _lines(page):
            first = spans[0]
            line = ''.join(s['text'] for s in spans)
            if 'Cormorant' in first['font'] and first['size'] > 13:
                flush_key()
                heading = re.sub(r'^[IVXLC]+\.\s*', '', line.strip())
                if heading.lower().startswith('перевір себе'):
                    mode = 'check'
                    cur = pt = None
                    continue
                cur = {'title': heading, 'intro': '', 'points': [], 'keys': []}
                sections.append(cur)
                pt, mode = None, 'text'
                continue
            if mode == 'check':
                m = re.match(r'^\s*(\d+)\.\s*(.+)', line)
                if m:
                    questions.append(m.group(2).strip())
                elif questions and line.strip() and first['size'] > 9 and not line.strip().startswith('Посилання'):
                    questions[-1] += ' ' + line.strip()
                continue
            if cur is None:
                continue
            if 'Italic' in first['font'] and all('Italic' in s['font'] for s in spans if s['text'].strip()):
                key_buf.append(line.strip())
                continue
            flush_key()
            if first['color'] == NUM_COLOR and re.match(r'^\s*\d+\.\s*$', first['text']):
                pt = {'level': 2 if bbox[0] > LEVEL2_X else 1, 'lead': '', 'text': '', 'refs': ''}
                cur['points'].append(pt)
                spans = spans[1:]
                mode = 'text'
                if spans and 'Bold' in spans[0]['font'] and spans[0]['color'] == 0x1f3a5f:
                    pt['lead'] = spans[0]['text'].strip()
                    spans = spans[1:]
            for s in spans:
                if s['text'].strip() == '▸':
                    mode = 'refs'
                    continue
                if mode == 'refs' and s['size'] < 9:
                    pt['refs'] += s['text']
                    continue
                mode = 'text'
                if pt is None:
                    cur['intro'] += _span_md(s)
                else:
                    pt['text'] += _span_md(s)
            if pt is None:
                cur['intro'] += ' '
            elif mode == 'text':
                pt['text'] += ' '
            else:
                pt['refs'] += ' '
    flush_key()
    for sec in sections:
        sec['intro'] = _clean(sec['intro'])
        for p in sec['points']:
            p['text'] = _clean(p['text'])
            p['refs'] = split_refs(p['refs'])
    return {'title': title, 'meta': meta, 'sections': sections, 'questions': [_clean(q) for q in questions]}


def _clean(t):
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'\*\*\s*\*\*', ' ', t)
    return t


def split_refs(text):
    """«Числа 13:25–33; 14:1–9, 23; Луки 1:30» -> ['Числа 13:25-33', 'Числа 14:1-9, 23', 'Луки 1:30']"""
    out, book = [], None
    for part in re.sub(r'\s+', ' ', text).replace('–', '-').split(';'):
        part = part.strip().rstrip('.')
        if not part:
            continue
        m = re.match(r'^((?:[123] )?[^\d:]+?)\s+(\d+:.+)$', part)
        if m:
            book = m.group(1).strip()
            out.append(f'{book} {m.group(2).strip()}')
        elif book and re.match(r'^\d+:', part):
            out.append(f'{book} {part}')
    return out
