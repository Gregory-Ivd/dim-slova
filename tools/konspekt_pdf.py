"""Конспект теми для роздачі: без обкладинки, з плашкою церкви й школи і прямим посиланням на урок.

python tools/konspekt_pdf.py <конспект.pdf> [...] [--out <тека>]

Бере оригінал з обкладинкою, прибирає обкладинку, на першу сторінку ставить плашку
(«Християнська церква «Перемога» · м. Рівне», «Біблійна школа «Дім Слова»», «Конспект теми», назва теми,
посилання «Самостійна робота і тести онлайн») і перенумеровує сторінки.
Посилання веде на сторінку уроку, якщо урок з такою назвою є в src/lessons.json, інакше – на головну.
Типова тека: ~/Documents/Дім Слова – конспекти; оригінал копіюється в її підтеку «Оригінали з обкладинкою».
Потрібно: pip install pymupdf fonttools (шрифти завантажуються в .cache/fonts при першому запуску).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(ROOT, '.cache', 'fonts')
SITE = 'https://gregory-ivd.github.io/dim-slova/'
OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Дім Слова – конспекти')
ORIG = 'Оригінали з обкладинкою'

NAVY = (0x1f / 255, 0x3a / 255, 0x5f / 255)
GOLD = (0xe3 / 255, 0xc8 / 255, 0x82 / 255)
GOLD_LINE = (0xd4 / 255, 0xa9 / 255, 0x4f / 255)
FOOT_GOLD = (0xb0 / 255, 0x85 / 255, 0x2b / 255)
WHITE = (1, 0.973, 0.91)
MUTED = (0xcd / 255, 0xd6 / 255, 0xe4 / 255)
BAND = 72          # висота плашки, pt
MARGIN = 45        # лівий/правий відступ тексту, як у конспекті

# Статичні накреслення з варіативних шрифтів Google Fonts (OFL).
FONT_SPECS = {
    'Montserrat-SemiBold': ('ofl/montserrat/Montserrat%5Bwght%5D.ttf', 600),
    'Montserrat-Bold': ('ofl/montserrat/Montserrat%5Bwght%5D.ttf', 700),
    'Cormorant-SemiBold': ('ofl/cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf', 600),
    'Cormorant-Italic': ('ofl/cormorantgaramond/CormorantGaramond-Italic%5Bwght%5D.ttf', 500),
}


def font(name):
    path = os.path.join(FONTS, name + '.ttf')
    if not os.path.exists(path):
        os.makedirs(FONTS, exist_ok=True)
        src, wght = FONT_SPECS[name]
        vf = os.path.join(FONTS, os.path.basename(src).replace('%5Bwght%5D', '-VF'))
        if not os.path.exists(vf):
            urllib.request.urlretrieve('https://github.com/google/fonts/raw/main/' + src, vf)
        subprocess.run([sys.executable, '-m', 'fontTools.varLib.instancer', vf, f'wght={wght}', '-o', path, '-q'], check=True)
    return pymupdf.Font(fontfile=path)


F_CAPS, F_NUM, F_TITLE, F_ITAL = (font(n) for n in ('Montserrat-SemiBold', 'Montserrat-Bold', 'Cormorant-SemiBold', 'Cormorant-Italic'))


def lesson_pages():
    """Назва уроку -> сторінка на сайті, з src/lessons.json."""
    pages = {}
    for e in json.load(open(os.path.join(ROOT, 'src', 'lessons.json'), encoding='utf-8')):
        cfg = os.path.join(ROOT, 'src', e['slug'], 'lesson.json')
        if os.path.exists(cfg):
            pages[json.load(open(cfg, encoding='utf-8'))['title']] = e['slug'] + '.html'
    return pages


def spaced(tw, x, y, text, fnt, size, tracking):
    """Рядок із розрядкою (як letter-spacing у CSS)."""
    for ch in text:
        tw.append((x, y), ch, font=fnt, fontsize=size)
        x += fnt.text_length(ch, fontsize=size) + tracking
    return x


def spaced_len(text, fnt, size, tracking):
    return sum(fnt.text_length(c, fontsize=size) + tracking for c in text) - tracking


def topic(doc):
    """Назва теми з обкладинки: найбільший рядок на першій сторінці."""
    spans = [s for b in doc[0].get_text('dict')['blocks'] for l in b.get('lines', []) for s in l['spans'] if s['text'].strip()]
    big = max(s['size'] for s in spans)
    return ' '.join(s['text'].strip() for s in spans if s['size'] >= big - 0.5)


def renumber(page, n):
    """Номер сторінки внизу праворуч -> n."""
    h = page.rect.height
    hits = [s for b in page.get_text('dict')['blocks'] for l in b.get('lines', []) for s in l['spans']
            if re.fullmatch(r'\d+', s['text'].strip()) and s['bbox'][1] > h - 40]
    if not hits:
        return
    s = max(hits, key=lambda s: s['bbox'][2])
    r = pymupdf.Rect(s['bbox'])
    page.add_redact_annot(r + (-1, -1, 1, 1), fill=False)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
    text, size = str(n), s['size']
    tw = pymupdf.TextWriter(page.rect)
    tw.append((r.x1 - F_NUM.text_length(text, fontsize=size), s['origin'][1]), text, font=F_NUM, fontsize=size)
    tw.write_text(page, color=FOOT_GOLD)


def band(page, title, url):
    W = page.rect.width
    page.draw_rect(pymupdf.Rect(0, 0, W, BAND), color=None, fill=NAVY)
    page.draw_line((0, BAND), (W, BAND), color=GOLD_LINE, width=1.2)

    def write(color, *items):
        tw = pymupdf.TextWriter(page.rect)
        for fn in items:
            fn(tw)
        tw.write_text(page, color=color)

    sub = 'КОНСПЕКТ ТЕМИ'
    write(GOLD,
          lambda tw: spaced(tw, MARGIN, 24, 'ХРИСТИЯНСЬКА ЦЕРКВА «ПЕРЕМОГА» · М. РІВНЕ', F_CAPS, 6.4, 1.25),
          lambda tw: tw.append((MARGIN, 44), 'Біблійна школа «Дім Слова»', font=F_ITAL, fontsize=15),
          lambda tw: spaced(tw, W - MARGIN - spaced_len(sub, F_CAPS, 6.4, 1.25), 24, sub, F_CAPS, 6.4, 1.25))
    size = 26
    while F_TITLE.text_length(title, fontsize=size) > W / 2 - MARGIN and size > 12:
        size -= 1
    write(WHITE, lambda tw: tw.append((W - MARGIN - F_TITLE.text_length(title, fontsize=size), 50), title, font=F_TITLE, fontsize=size))
    # Посилання на веб-версію з тестами.
    label = 'Самостійна робота і тести онлайн:  '
    shown = url.replace('https://', '')
    x = MARGIN + F_CAPS.text_length(label, fontsize=6.6)
    w = F_NUM.text_length(shown, fontsize=6.6)
    write(MUTED, lambda tw: tw.append((MARGIN, 61), label, font=F_CAPS, fontsize=6.6))
    write(GOLD, lambda tw: tw.append((x, 61), shown, font=F_NUM, fontsize=6.6))
    page.draw_line((x, 62.6), (x + w, 62.6), color=GOLD, width=0.4)
    page.insert_link({'kind': pymupdf.LINK_URI, 'from': pymupdf.Rect(x - 1, 53, x + w + 1, 65), 'uri': url})


def process(src, dst, pages):
    doc = pymupdf.open(src)
    title = topic(doc)
    url = SITE + pages.get(title, '')
    doc.delete_page(0)
    for i, p in enumerate(doc):
        renumber(p, i + 1)
    out = pymupdf.open()
    W, H = doc[0].rect.width, doc[0].rect.height
    page = out.new_page(width=W, height=H)
    # Перша сторінка: плашка + вміст під нею; верхнє поле оригіналу (~16 pt) зрізаємо, щоб текст менше зменшувався.
    page.show_pdf_page(pymupdf.Rect(0, BAND + 6, W, H), doc, 0, keep_proportion=True, clip=pymupdf.Rect(0, 16, W, H))
    band(page, title, url)
    out.insert_pdf(doc, from_page=1)
    out.set_metadata(dict(doc.metadata or {}, title=f'{title} – конспект теми'))
    out.subset_fonts()
    out.save(dst, garbage=4, deflate=True, clean=True)
    return title, len(out), url


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pdf', nargs='+', help='оригінали конспектів з обкладинкою')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    orig_dir = os.path.join(a.out, ORIG)
    os.makedirs(orig_dir, exist_ok=True)
    pages = lesson_pages()
    for f in a.pdf:
        name = os.path.basename(f)
        keep = os.path.join(orig_dir, name)
        if os.path.abspath(f) != os.path.abspath(keep):
            shutil.copy2(f, keep)
        title, n, url = process(keep, os.path.join(a.out, name), pages)
        print(f'{name}: «{title}», {n} с., посилання {url}')


if __name__ == '__main__':
    main()
