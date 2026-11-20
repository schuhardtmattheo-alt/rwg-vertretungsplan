# Lädt das Projekt in ein ÖFFENTLICHES GitHub-Repository hoch (nur Code, KEINE Zugangsdaten),
# hinterlegt die Zugangsdaten als verschlüsselte GitHub-Secrets und startet den ersten Lauf.
# Vorher zugangsdaten.env ausfüllen!
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$RepoName = "rwg-vertretungsplan"

function Wert($key) {
    $m = Select-String -Path "zugangsdaten.env" -Pattern "^$key=(\S.*)$"
    if (-not $m) { return "" }
    $v = $m.Matches[0].Groups[1].Value.Trim()
    if ($v.Length -ge 2 -and $v[0] -eq $v[-1] -and ($v[0] -eq '"' -or $v[0] -eq "'")) { $v = $v.Substring(1, $v.Length - 2) }
    return $v
}

# 1) Prüfen, ob alles ausgefüllt ist
foreach ($key in "RWG_EMAIL", "RWG_PASSWORT", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID") {
    if (-not (Wert $key)) {
        Write-Host "Bitte zuerst $key in zugangsdaten.env eintragen." -ForegroundColor Red
        exit 1
    }
}

# 2) Bei GitHub anmelden (öffnet den Browser, falls noch nicht angemeldet)
gh auth status 2>$null
if ($LASTEXITCODE -ne 0) { gh auth login --web --git-protocol https }
$login = gh api user --jq .login
$Repo = "$login/$RepoName"

# 3) Git-Repository anlegen
if (-not (Test-Path ".git")) { git init -b main }
# Öffentliche Commits ohne echte E-Mail-Adresse (GitHub-"noreply"-Adresse)
git config user.name $login
git config user.email "$login@users.noreply.github.com"
git add .
# Sicherheitscheck: Zugangsdaten dürfen nie hochgeladen werden
if (git diff --cached --name-only | Select-String -Pattern "\.env$|debug/|public/") {
    Write-Host "STOPP: Zugangsdaten oder Debug-Dateien wären hochgeladen worden!" -ForegroundColor Red
    exit 1
}
git commit -m "Vertretungsplan-Abruf" 2>$null

# 4) Auf GitHub hochladen (öffentlich = unbegrenzt kostenlose Laufzeit)
gh repo view $Repo 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    gh repo create $RepoName --public --source . --push
} else {
    git push -u origin main
}

# 5) Token für den "Aktualisieren"-Knopf (braucht das Repository, deshalb erst jetzt)
if (-not (Wert "KNOPF_GITHUB_TOKEN")) {
    Write-Host ""
    Write-Host "Jetzt noch der Token fuer den Aktualisieren-Knopf:" -ForegroundColor Yellow
    Write-Host "  Token name:          vertretungsplan-knopf"
    Write-Host "  Expiration:          No expiration (oder 1 Jahr)"
    Write-Host "  Repository access:   Only select repositories -> $RepoName"
    Write-Host "  Permissions:         Repository -> Actions -> Read and write"
    Write-Host "  -> Generate token, kopieren und in zugangsdaten.env hinter KNOPF_GITHUB_TOKEN= einfuegen, speichern."
    Start-Process "https://github.com/settings/personal-access-tokens/new"
    Read-Host "Wenn erledigt, Enter druecken"
    if (-not (Wert "KNOPF_GITHUB_TOKEN")) {
        Write-Host "Kein Token gefunden - der Knopf funktioniert erst, wenn du ihn eintraegst und dieses Skript nochmal startest." -ForegroundColor Yellow
    }
}

# 6) Zugangsdaten als Secrets hinterlegen (verschlüsselt, auch im öffentlichen Repo für niemanden lesbar)
foreach ($key in "RWG_EMAIL", "RWG_PASSWORT", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "KNOPF_GITHUB_TOKEN") {
    $v = Wert $key
    if ($v) { gh secret set $key --body $v --repo $Repo }
}

# 7) Ersten Lauf starten
gh workflow run plan.yml --repo $Repo
Write-Host ""
Write-Host "Fertig! In ca. 2 Minuten ist die Seite erreichbar: https://rwg-plan-9c.pages.dev" -ForegroundColor Green
Start-Process "https://github.com/$Repo/actions"
