# Prints a lesson page (<slug>.html) to <slug>.pdf with headless Chrome.
# Usage: pdf.ps1 [-Lesson vira]   (without -Lesson prints every lesson from src/lessons.json)
# Needs Chrome 131+ for CSS @page margin boxes (running header/footer).
param([string]$Lesson)
$root = Split-Path -Parent $PSScriptRoot
# Chrome або Edge (обидва на Chromium) – перший, що знайдеться.
$chrome = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $chrome) { throw "Chrome or Edge not found" }
$profileDir = Join-Path $env:TEMP "sb-chrome-profile"
$slugs = if ($Lesson) { @($Lesson) } else {
  (Get-Content (Join-Path $root "src\lessons.json") -Raw -Encoding UTF8 | ConvertFrom-Json) | ForEach-Object { $_.slug }
}
foreach ($slug in $slugs) {
  $url = ([System.Uri](Join-Path $root "$slug.html")).AbsoluteUri
  $out = Join-Path $root "$slug.pdf"
  & $chrome --headless=new --disable-gpu --no-first-run --user-data-dir="$profileDir" --no-pdf-header-footer --virtual-time-budget=20000 --print-to-pdf="$out" "$url" 2>$null | Out-Null
  Get-Item $out | Select-Object Name, Length
}
