# Vertretungsplan 9C – automatisch online

**Was passiert:** GitHub (kostenlos) startet um 7:20, 7:30, 11:20, 15:30, 18:00 und 20:00 Uhr einen kleinen
Computer in der Cloud (ab 15:30 Uhr und am Wochenende wird der nächste Schultag angezeigt). Zusätzlich gibt es auf der Webseite einen Knopf **„Aktualisieren“**, der
sofort einen Abruf startet (dauert ca. 1–2 Minuten). Der Cloud-Computer öffnet
`rwg-waren.de/stundenplan/vplan/modern/`, meldet sich falls nötig bei Microsoft an, wählt **9C**,
stellt auf **Heute**, liest den Plan aus und veröffentlicht ihn auf **Cloudflare Pages** (kostenlos).
**Dein PC muss dafür nicht an sein.**

**Ausfall-Regel:** Eine Stunde gilt als *Ausfall*, wenn die Schulseite sie so anzeigt, wenn „selbst.“
in der Info steht oder wenn kein Lehrer eingetragen ist.

---

## 1. Passwort eintragen
Öffne `zugangsdaten.env` und trag hinter `RWG_PASSWORT=` dein Passwort ein.
Die Datei bleibt auf deinem PC. Online landet das Passwort nur verschlüsselt als „GitHub-Secret“.

## 2. Cloudflare (einmalig, kostenlos)
1. Konto anlegen auf https://dash.cloudflare.com/sign-up
2. **Account-ID:** im Dashboard links auf „Workers & Pages“ → rechts steht „Account ID“.
   Kopieren und hinter `CLOUDFLARE_ACCOUNT_ID=` einfügen.
3. **API-Token:** https://dash.cloudflare.com/profile/api-tokens → „Create Token“ →
   „Start from scratch“ → „Start with an Account policy“ → Berechtigung **Cloudflare Pages → Edit**
   → Token erstellen und hinter `CLOUDFLARE_API_TOKEN=` einfügen.

## 3. (Optional) Lokal testen
Rechtsklick auf `lokal_testen.ps1` → „Mit PowerShell ausführen“.
Es öffnet sich ein Browserfenster, das alles durchklickt. Danach wird die fertige Seite angezeigt.
(Der Knopf funktioniert dort noch nicht, erst online.)

## 4. Online stellen (einmalig)
Du brauchst ein kostenloses GitHub-Konto (https://github.com/signup). Dann in PowerShell:

```
powershell -ExecutionPolicy Bypass -File .\einrichten.ps1
```

Das Skript
1. lädt den **Programmcode** in ein öffentliches GitHub-Repository hoch (keine Zugangsdaten!),
2. öffnet die Seite für den **Knopf-Token** und sagt dir, was du anklicken musst
   (Token in `zugangsdaten.env` hinter `KNOPF_GITHUB_TOKEN=` einfügen, speichern, Enter drücken),
3. speichert alle Zugangsdaten verschlüsselt als Secrets,
4. startet den ersten Abruf.

Nach ca. 2 Minuten ist die Seite erreichbar unter **https://rwg-plan-9c.pages.dev**.
Diesen Link kannst du deiner Mutter schicken (z. B. als Lesezeichen auf dem Handy-Startbildschirm).
Ist der Name schon vergeben, in GitHub unter *Settings → Secrets and variables → Actions → Variables*
eine Variable `CF_PROJEKT` mit einem anderen Namen anlegen.

---

## Gut zu wissen
- **Öffentliches Repository:** Jeder kann den *Programmcode* und die Lauf-Protokolle sehen, aber
  **nicht** die Secrets (Passwort, E-Mail, Tokens). Die Protokolle enthalten absichtlich keine
  Plandetails und keine Screenshots.
- **Zwei-Faktor-Anmeldung:** Wenn Microsoft eine Bestätigung per App/SMS verlangt, kann das
  Programm das nicht automatisch – dann schlägt der Abruf fehl.
- **Fehler ansehen:** GitHub → Repository → *Actions* → fehlgeschlagener Lauf → Schritt
  „Plan auslesen“ zeigt die Fehlermeldung. Für einen Screenshot `lokal_testen.ps1` ausführen.
- **Passwort geändert?** `zugangsdaten.env` anpassen und `einrichten.ps1` nochmal ausführen.
- **Datenschutz:** Der Plan steht sonst nur hinter dem Schul-Login. Den Link deshalb nur privat
  weitergeben. Die Seite ist für Suchmaschinen gesperrt (`noindex`).
- **Andere Klasse:** in GitHub eine Variable `KLASSE` (z. B. `10a`) anlegen.
- GitHub startet geplante Läufe manchmal ein paar Minuten zu spät – dafür gibt es den Knopf.
- Ist der angezeigte Plan nicht von heute, erscheint oben ein roter Warnhinweis.
