# Prints index.html to slovo-bozhe.pdf with headless Chrome.
# Needs Chrome 131+ for CSS @page margin boxes (running header/footer).
$root = Split-Path -Parent $PSScriptRoot
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$src = Join-Path $root "index.html"
$url = ([System.Uri]$src).AbsoluteUri
$out = Join-Path $root "slovo-bozhe.pdf"
$profileDir = Join-Path $env:TEMP "sb-chrome-profile"
& $chrome --headless=new --disable-gpu --no-first-run --user-data-dir="$profileDir" --no-pdf-header-footer --virtual-time-budget=20000 --print-to-pdf="$out" "$url" 2>$null | Out-Null
Get-Item $out | Select-Object Name, Length
