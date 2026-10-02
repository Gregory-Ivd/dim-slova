# Біблійна школа «Дім Слова», церква «Перемога», Рівне

Навчальні посібники з тестами для самоперевірки: вебсторінки й PDF. Вступ – «Слово Боже», урок 1 – «Віра».

Українською перекладено та оформлено за навчальним матеріалом Біблійної школи «Робітники Царства» християнської церкви «Перемога» (м. Київ). Використано з дозволу.

Цитати Святого Письма — «Біблія. Сучасний переклад» © Українське Біблійне Товариство, 2020–2023.

## Структура

- `index.html` – головна сторінка школи зі списком уроків; кожен урок – `<slug>.html` і `<slug>.pdf`.
- `src/lessons.json` – порядок уроків і підписи («Вступ», «Урок 1», …).
- `src/<slug>/` – урок: `lesson.json` (назва, тези обкладинки, епіграф, нумерація посилань `synodal`/`ubt`),
  `preface.html`, `ch1.md` … (`@@` цитата, `!!` головна думка, `>>` пояснення, `###` пункт), `quiz1.json` … – тести.
- `sources/` – конспекти наступних уроків (PDF, не в репозиторії).
- `assets/` – шаблони, стилі, скрипти (`template.html` – урок, `home.*` – головна, `pastor.*` – сторінка пастора).
- `tools/build.py` – збирає всі сторінки; тексти віршів бере з bible.com (кеш у `.cache/`, не в репозиторії).
- `tools/pdf.ps1 [-Lesson <slug>]` – друкує уроки в PDF через Chrome або Edge.

## Новий урок

1. `src/<slug>/` з `lesson.json`, `preface.html`, `chN.md`, `quizN.json` (вимоги до тестів – `tools/SPEC.md`).
2. Рядок у `src/lessons.json`.
3. `python tools/build.py`, потім `powershell -ExecutionPolicy Bypass -File tools/pdf.ps1 -Lesson <slug>`.

## Збірка

```
python tools/build.py
powershell -ExecutionPolicy Bypass -File tools/pdf.ps1
```

У вступному уроці синодальна нумерація перераховується на нумерацію УБТ (`tools/refs.py`, `remap`); у нових уроках посилання вже за УБТ.

## Результати тестів

Учень при першому вході вказує ім’я та прізвище. Після кожного тесту результат надсилається в Google Таблицю
(якщо немає інтернету – пізніше, з черги в браузері). Пастор бачить усіх на `pastor.html#key=<ключ>`.

- Адреса веб-застосунку – `ENDPOINT` у `tools/build.py`.
- Ключ пастора – `apps-script/key.gs` (не в репозиторії). Щоб змінити: новий ключ у `key.gs`, потім
  `clasp push` і `clasp update-deployment <id>` у теці `apps-script/`, і нове посилання пастору.
- Після зміни `Code.gs`: `npx @google/clasp push --force` і `npx @google/clasp update-deployment <id>` – адреса не зміниться.

## Збірка

```
python tools/build.py
powershell -ExecutionPolicy Bypass -File tools/pdf.ps1
```

Синодальна нумерація в `src/*.md` перераховується на нумерацію УБТ у `tools/refs.py` (`remap`).
