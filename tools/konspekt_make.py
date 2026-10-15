"""Верстає конспект теми (оригінал з обкладинкою) з текстового джерела – у дизайні попередніх конспектів.

python tools/konspekt_make.py <джерело.md> [--out <тека>]

Джерело (UTF-8):
    title: Благодать
    meta: Що таке благодать · Принципи дії благодаті · …
    year: 2026                      (необов'язково)

    # Що таке благодать             – тема (римський номер ставиться сам)
    Вступний абзац теми.
    1. **Початок пункту.** Текст з **жирним** словом. ▸ Римлян 1:7; 1 Коринтян 1:4
       1. **Підпункт.** Текст. ▸ …  – пункт другого рівня (відступ пробілами)
    > Головна думка курсивом.

    # Перевір себе
    1. Питання?

Результат – «<title>-конспект.pdf» (типово в materials/konspekty/Оригінали з обкладинкою),
його розбирає tools/konspekt.py, тож далі – звичайний шлях: new_lesson.py → … → publish.ps1 -Konspekt <pdf>.
Потрібно: Chrome або Edge (друк HTML у PDF), інтернет (шрифти Google Fonts).
"""
import argparse
import html
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'materials', 'konspekty', 'Оригінали з обкладинкою')
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
FOOTER = 'Біблійна школа «Дім Слова» · Християнська церква «Перемога», м. Рівне'
NOTE = ('<p>Посилання подано за нумерацією перекладу «Біблія. Сучасний переклад» (УБТ).</p>'
        '<p>Українською перекладено та оформлено за навчальним матеріалом Біблійної школи «Робітники Царства» '
        'християнської церкви «Перемога» (м. Київ). Використано з дозволу.</p>')

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,400&family=Montserrat:wght@500;600&family=PT+Serif:ital,wght@0,400;0,700;1,400&display=block');
@page { size: A4; margin: 13mm 15mm 16mm 15mm;
  @bottom-left { content: "%FOOTER%"; font: 500 7pt Montserrat, sans-serif; color: #8a93a3; vertical-align: top; padding-top: 4mm; }
  @bottom-right { content: counter(page); font: 600 8pt Montserrat, sans-serif; color: #b0852b; vertical-align: top; padding-top: 4mm; } }
@page cover { margin: 0; @bottom-left { content: none; } @bottom-right { content: none; } }
* { box-sizing: border-box; }
html, body { margin: 0; }
body { font: 10.4pt/1.45 'PT Serif', serif; color: #1f2430; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.cover { page: cover; width: 210mm; height: 297mm; position: relative; break-after: page;
  background: radial-gradient(ellipse at 30% 0%, #26497a 0%, #1d3961 45%, #142847 100%); color: #fff8e8; text-align: center; }
.cover .f1 { position: absolute; inset: 12mm; border: 0.75pt solid rgba(227,200,130,.45); border-radius: 3mm; }
.cover .f2 { position: absolute; inset: 14.5mm; border: 0.5pt solid rgba(227,200,130,.25); border-radius: 2mm; }
.cover .in { position: absolute; left: 25mm; right: 25mm; top: 76mm; }
.cover .church { font: 600 8pt Montserrat, sans-serif; letter-spacing: .22em; color: #e3c882; }
.cover svg { display: block; margin: 15mm auto 0; width: 19mm; height: 17mm; }
.cover .school { margin-top: 9mm; font: 500 10pt Montserrat, sans-serif; letter-spacing: .38em; color: #f1e7cf; }
.cover .name { margin-top: 1mm; font: italic 400 22pt 'Cormorant Garamond', serif; color: #e3c882; }
.cover h1 { margin: 9mm 0 0; font: 300 64pt/1 'Cormorant Garamond', serif; color: #fff8e8; }
.cover .sub { margin-top: 3mm; font: italic 400 18pt 'Cormorant Garamond', serif; color: #e3c882; }
.cover .meta { margin: 9mm auto 0; max-width: 125mm; font: 10pt/1.75 'PT Serif', serif; color: #cdd6e4; }
.cover .insta { margin-top: 12mm; font: 500 7.5pt Montserrat, sans-serif; letter-spacing: .12em; color: #aebbd0; }
.cover .insta span { margin-left: 8mm; }
h2 { font: 300 16.5pt/1.2 'Cormorant Garamond', serif; color: #1f3a5f; margin: 12pt 0 6pt; padding-bottom: 3pt;
  border-bottom: 0.75pt solid #dcc896; break-after: avoid; }
h2:first-child { margin-top: 0; }
h2 .n { color: #b0852b; }
p { margin: 0 0 6pt; }
ol { margin: 0 0 6pt; padding: 0 0 0 15pt; }
ol li { margin-bottom: 4pt; }
ol li.l2 { margin-left: 17pt; }
li::marker { content: attr(data-n) ". "; font: 600 8.5pt Montserrat, sans-serif; color: #b0852b; }
b { font-weight: 700; }
b.lead { color: #1f3a5f; }
.refs { white-space: nowrap; }
.refs .tri { font-size: 8pt; color: #b0852b; margin: 0 2pt 0 3pt; }
.refs .r { font: 500 8pt Montserrat, sans-serif; color: #7a5a1a; white-space: normal; }
.nb { white-space: nowrap; }
.key { background: #f8f1e1; border-left: 1.7pt solid #b0852b; padding: 6pt 10pt; margin: 6pt 0 10pt;
  font-style: italic; color: #3f3320; break-inside: avoid; }
ol.q li { margin-bottom: 4pt; }
.note { margin-top: 14pt; padding-top: 8pt; border-top: 0.75pt solid #dcc896; font-size: 8.4pt; color: #5d6474; }
.note p { margin: 0 0 4pt; }
"""

BOOK_SVG = ('<svg viewBox="0 0 54 48" fill="none" stroke="#e3c882" stroke-width="2.6" stroke-linecap="round" '
            'stroke-linejoin="round"><path d="M27 3v11M21.5 8h11"/><path d="M27 21c-6-4-14-5-22-3v26c8-2 16-1 22 3 '
            '6-4 14-5 22-3V18c-8-2-16-1-22 3z"/><path d="M27 21v26"/></svg>')


def inline(t):
    t = html.escape(t, quote=False)
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)


def point(text):
    """'**Початок.** Текст ▸ посилання' -> HTML пункту без номера."""
    refs = ''
    if '▸' in text:
        text, refs = text.split('▸', 1)
    text = text.strip()
    lead = ''
    m = re.match(r'^\*\*(.+?)\*\*\s*(.*)$', text)
    if m:
        lead, text = m.group(1), m.group(2)
    out = (f'<b class="lead">{html.escape(lead, quote=False)}</b> ' if lead else '') + inline(text)
    if refs.strip():
        out += (f'<span class="refs"><span class="tri">▸</span><span class="r">'
                + '; '.join(f'<span class="nb">{html.escape(r.strip(), quote=False)}</span>' for r in refs.split(';'))
                + '</span></span>')
    return out


def parse(src):
    head, body = {}, []
    lines = src.splitlines()
    i = 0
    while i < len(lines) and not lines[i].startswith('#'):
        m = re.match(r'^(\w+):\s*(.*)$', lines[i])
        if m:
            head[m.group(1)] = m.group(2).strip()
        i += 1
    return head, lines[i:]


def render(src):
    head, lines = parse(src)
    title = head['title']
    parts, n_topic, in_list, check = [], 0, None, False

    def close():
        nonlocal in_list
        if in_list:
            parts.append('</ol>')
            in_list = None

    for raw in lines:
        if not raw.strip():
            continue
        if raw.startswith('# '):
            close()
            h = raw[2:].strip()
            if h.lower().startswith('перевір себе'):
                check = True
                parts.append(f'<h2>{html.escape(h)}</h2>')
            else:
                parts.append(f'<h2><span class="n">{ROMAN[n_topic]}.</span> {html.escape(h)}</h2>')
                n_topic += 1
            continue
        m = re.match(r'^(\s*)(\d+)\.\s+(.*)$', raw)
        if m:
            kind = 'q' if check else 'pts'
            if in_list != kind:
                close()
                parts.append(f'<ol class="{kind}">')
                in_list = kind
            lvl = ' class="l2"' if len(m.group(1)) >= 2 and not check else ''
            body = inline(m.group(3)) if check else point(m.group(3))
            parts.append(f'<li{lvl} data-n="{m.group(2)}">{body}</li>')
            continue
        close()
        if raw.startswith('>'):
            parts.append(f'<div class="key">{inline(raw[1:].strip())}</div>')
        else:
            parts.append(f'<p>{inline(raw.strip())}</p>')
    close()
    css = CSS.replace('%FOOTER%', FOOTER)
    cover = (f'<section class="cover"><div class="f1"></div><div class="f2"></div><div class="in">'
             f'<div class="church">ХРИСТИЯНСЬКА ЦЕРКВА «ПЕРЕМОГА» · М. РІВНЕ</div>{BOOK_SVG}'
             f'<div class="school">БІБЛІЙНА ШКОЛА</div><div class="name">«Дім Слова»</div>'
             f'<h1>{html.escape(title)}</h1><div class="sub">Конспект теми</div>'
             f'<div class="meta">{html.escape(head.get("meta", ""))}</div>'
             f'<div class="insta">INSTAGRAM.COM/VICTORYCHURCH_RV<span>{head.get("year", "2026")}</span></div>'
             f'</div></section>')
    return (f'<!doctype html><html lang="uk"><head><meta charset="utf-8">'
            f'<title>{html.escape(title)} – конспект · Біблійна школа «Дім Слова»</title><style>{css}</style></head>'
            f'<body>{cover}<main>{"".join(parts)}<div class="note">{NOTE}</div></main></body></html>'), title


def chrome():
    for p in (r'%ProgramFiles%\Google\Chrome\Application\chrome.exe',
              r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe',
              r'%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe',
              r'%ProgramFiles%\Microsoft\Edge\Application\msedge.exe'):
        p = os.path.expandvars(p)
        if os.path.exists(p):
            return p
    sys.exit('Chrome or Edge not found')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    with open(a.src, encoding='utf-8-sig') as f:
        page, title = render(f.read())
    os.makedirs(a.out, exist_ok=True)
    tmp = os.path.join(tempfile.gettempdir(), 'sb-konspekt.html')
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(page)
    pdf = os.path.join(a.out, title.replace(' ', '-') + '-конспект.pdf')
    subprocess.run([chrome(), '--headless=new', '--disable-gpu', '--no-first-run',
                    '--user-data-dir=' + os.path.join(tempfile.gettempdir(), 'sb-chrome-profile'),
                    '--no-pdf-header-footer', '--virtual-time-budget=20000', '--print-to-pdf=' + pdf,
                    'file:///' + tmp.replace('\\', '/')], check=True, capture_output=True)
    print(pdf)


if __name__ == '__main__':
    main()
