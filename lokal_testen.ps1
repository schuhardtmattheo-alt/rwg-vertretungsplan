# Testet das Auslesen einmal auf diesem PC (mit sichtbarem Browser-Fenster).
# Ergebnis: public\index.html  -> per Doppelklick im Browser ansehen.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m pip install -r requirements.txt
python -m playwright install chromium
python scraper.py --sichtbar
if ($LASTEXITCODE -eq 0) {
    Start-Process (Join-Path $PSScriptRoot "public\index.html")
} else {
    Write-Host "Fehler - siehe Bild in debug\fehler.png" -ForegroundColor Red
}
