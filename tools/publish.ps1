# Публікує урок: перевірка → збірка сайту → PDF уроку → конспект для роздачі → коміт і push на GitHub Pages.
# Usage: tools/publish.ps1 -Lesson <slug> [-Konspekt <оригінал-конспекту.pdf>] [-NoPush]
param(
  [Parameter(Mandatory = $true)][string]$Lesson,
  [string]$Konspekt,
  [switch]$NoPush
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONIOENCODING = 'utf-8'

python tools/check_lesson.py $Lesson
if ($LASTEXITCODE -ne 0) { throw "Урок $Lesson не пройшов перевірку – виправте помилки вище." }

python tools/build.py
if ($LASTEXITCODE -ne 0) { throw 'Збірка не вдалася.' }

& (Join-Path $PSScriptRoot 'pdf.ps1') -Lesson $Lesson

if ($Konspekt) {
  python tools/konspekt_pdf.py $Konspekt
  if ($LASTEXITCODE -ne 0) { throw 'Конспект не оброблено.' }
}

$title = (Get-Content "src/$Lesson/lesson.json" -Raw -Encoding UTF8 | ConvertFrom-Json).title
git add -A
# Повідомлення коміту – через файл у UTF-8: Windows PowerShell 5.1 псує кирилицю в аргументах.
$msg = Join-Path $env:TEMP 'sb-commit-msg.txt'
[IO.File]::WriteAllText($msg, "Add lesson «$title»`n", (New-Object Text.UTF8Encoding $false))
git commit -F $msg
if (-not $NoPush) {
  git push origin main
  Write-Host "Опубліковано. Сторінка з’явиться за 1–2 хвилини: https://gregory-ivd.github.io/dim-slova/$Lesson.html"
}
