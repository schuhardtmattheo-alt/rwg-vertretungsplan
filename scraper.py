"""
Holt den Vertretungsplan von rwg-waren.de (RWGplaner) für eine Klasse
und erzeugt daraus eine einfache Webseite im Ordner "public/".

Zugangsdaten kommen aus Umgebungsvariablen (in GitHub: Secrets) oder,
lokal, aus der Datei "zugangsdaten.env" neben diesem Skript.

Aufruf:
    python scraper.py            # unsichtbarer Browser
    python scraper.py --sichtbar # Browser-Fenster anzeigen (zum Testen)
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

from webseite import baue_webseite

HIER = Path(__file__).resolve().parent
PLAN_URL = "https://rwg-waren.de/stundenplan/vplan/modern/"
BERLIN = ZoneInfo("Europe/Berlin")
DEBUG_DIR = HIER / "debug"
PUBLIC_DIR = HIER / "public"


# ---------------------------------------------------------------- Zugangsdaten
def lade_env_datei(pfad: Path) -> None:
    """Liest KEY=WERT-Zeilen und setzt sie als Umgebungsvariablen (falls noch nicht gesetzt)."""
    if not pfad.exists():
        return
    for zeile in pfad.read_text(encoding="utf-8-sig").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        key, wert = zeile.split("=", 1)
        key, wert = key.strip(), wert.strip()
        if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
            wert = wert[1:-1]
        if wert and not os.environ.get(key):
            os.environ[key] = wert


# ---------------------------------------------------------------- Microsoft-Login
def ist_sichtbar(page, selector: str) -> bool:
    try:
        return page.locator(selector).first.is_visible()
    except Exception:
        return False


def anmelden_falls_noetig(page, email: str, passwort: str) -> None:
    """
    Wartet, bis die Klassenauswahl des RWGplaners erscheint.
    Landet der Browser unterwegs auf der Microsoft-Anmeldung, wird
    E-Mail -> Weiter -> Passwort -> Anmelden (-> "Angemeldet bleiben?") erledigt.
    """
    email_erledigt = passwort_erledigt = False
    ende = time.time() + 120

    while time.time() < ende:
        # Ziel erreicht: Klassenknöpfe sind da
        if ist_sichtbar(page, "#classList button.class-button"):
            return

        url = page.url
        if "login.microsoftonline.com" in url or "login.live.com" in url or "microsoft" in url:
            # Fehlermeldungen von Microsoft erkennen
            for fehler in ("#usernameError", "#passwordError", "#idTD_Error"):
                if ist_sichtbar(page, fehler):
                    text = page.locator(fehler).first.inner_text().strip()
                    raise RuntimeError(f"Microsoft-Anmeldung fehlgeschlagen: {text}")

            # Zwei-Faktor-Abfrage -> kann nicht automatisch erledigt werden
            if ist_sichtbar(page, "#idDiv_SAOTCAS_Title, #idDiv_SAOTCC_Title, #idTxtBx_SAOTCC_OTC"):
                raise RuntimeError(
                    "Microsoft verlangt eine Zwei-Faktor-Bestätigung (Authenticator/SMS). "
                    "Das kann das Programm nicht automatisch erledigen."
                )

            # Konto-Auswahl ("Konto auswählen")
            if ist_sichtbar(page, "#tilesHolder") and email:
                kachel = page.locator(f"#tilesHolder [data-test-id='{email}'], #tilesHolder :text-is('{email}')")
                if kachel.count():
                    kachel.first.click()
                    page.wait_for_timeout(1500)
                    continue

            # Schritt 1: E-Mail
            if ist_sichtbar(page, "input[name='loginfmt']") and not email_erledigt:
                if not email:
                    raise RuntimeError("RWG_EMAIL fehlt (zugangsdaten.env bzw. GitHub-Secret).")
                page.fill("input[name='loginfmt']", email)
                page.click("#idSIButton9")  # "Weiter"
                email_erledigt = True
                page.wait_for_timeout(2000)
                continue

            # Schritt 2: Passwort
            if ist_sichtbar(page, "input[name='passwd']") and not passwort_erledigt:
                if not passwort:
                    raise RuntimeError("RWG_PASSWORT fehlt (zugangsdaten.env bzw. GitHub-Secret).")
                page.fill("input[name='passwd']", passwort)
                page.click("#idSIButton9")  # "Anmelden"
                passwort_erledigt = True
                page.wait_for_timeout(2500)
                continue

            # Schritt 3: "Angemeldet bleiben?" -> Ja
            if ist_sichtbar(page, "#KmsiCheckboxField, #KmsiDescription") or ist_sichtbar(
                page, "text=/Angemeldet bleiben|Stay signed in/i"
            ):
                page.click("#idSIButton9")
                page.wait_for_timeout(2000)
                continue

        page.wait_for_timeout(1000)

    raise RuntimeError(f"Klassenauswahl ist nach 2 Minuten nicht erschienen (aktuelle Seite: {page.url}).")


# ---------------------------------------------------------------- Plan auslesen
JS_AUSLESEN = r"""
() => {
  const t = (el) => (el ? el.textContent.replace(/\s+/g, " ").trim() : "");
  const lessons = Array.from(document.querySelectorAll("#planList article.lesson-card")).map((card) => ({
    stunde: t(card.querySelector(".lesson-period")).replace(/\.$/, ""),
    fach: t(card.querySelector(".lesson-title strong")),
    kurs: t(card.querySelector(".lesson-title .course-tag")),
    lehrer: t(card.querySelector(".lesson-class")),
    raum: t(card.querySelector(".lesson-room")),
    zeit: t(card.querySelector(".lesson-clock")),
    info: t(card.querySelector(".lesson-info-text")),
    seite_markiert_ausfall: card.classList.contains("is-cancelled"),
    seite_markiert_aenderung: card.classList.contains("is-changed"),
    fach_geaendert: !!card.querySelector(".lesson-title strong.is-changed"),
    lehrer_geaendert: !!card.querySelector(".lesson-class.is-changed"),
    raum_geaendert: !!card.querySelector(".lesson-room.is-changed"),
  }));
  const infoKarten = Array.from(document.querySelectorAll("#planList article.info-card")).map((card) => ({
    titel: t(card.querySelector("h3")),
    zeilen: Array.from(card.querySelectorAll("p")).map(t).filter(Boolean),
  }));
  return {
    klasse_label: t(document.querySelector("#selectedClassLabel")),
    datum_text: t(document.querySelector("#planDate")),
    aktualisiert: t(document.querySelector("#updatedAt")),
    datum_feld: (document.querySelector("#planDateInput") || {}).value || "",
    leer_text: t(document.querySelector("#planList .empty-state")),
    stunden: lessons,
    info_karten: infoKarten,
  };
}
"""


def bewerte_stunde(s: dict) -> dict:
    """
    Regel: "Ausfall" wenn die Seite es so markiert, wenn "selbst" in der Info
    steht oder wenn kein Lehrer eingetragen ist (kein Lehrer + kein Raum = Ausfall).
    """
    info = s.get("info", "")
    ausfall = (
        s.get("seite_markiert_ausfall")
        or s.get("fach", "").lower() in ("ausfall", "entfall", "---")
        or re.search(r"\bselbst", info, re.I) is not None
        or not s.get("lehrer")
    )
    if ausfall:
        status = "ausfall"
    elif s.get("seite_markiert_aenderung") or info:
        status = "aenderung"
    else:
        status = "normal"
    s["status"] = status
    return s


UMSCHALTZEIT = (15, 30)  # ab dieser Uhrzeit wird der nächste Schultag angezeigt


def soll_naechster_tag(jetzt: datetime) -> bool:
    modus = os.environ.get("TAG_MODUS", "").lower()  # zum Testen: "heute" oder "naechster"
    if modus in ("heute", "naechster"):
        return modus == "naechster"
    wochenende = jetzt.weekday() >= 5
    return wochenende or (jetzt.hour, jetzt.minute) >= UMSCHALTZEIT


def lese_plan(page, klasse: str) -> dict:
    # Cookie-Hinweis wegklicken, falls vorhanden
    if ist_sichtbar(page, "#acceptCookies"):
        page.click("#acceptCookies")

    # Klasse wählen (Knopf-Text ist z. B. "9c" oder "9C")
    knopf = page.locator("#classList button.class-button").filter(
        has_text=re.compile(rf"^\s*{re.escape(klasse)}\s*$", re.I)
    )
    if knopf.count() == 0:
        vorhandene = page.locator("#classList button.class-button").all_inner_texts()
        raise RuntimeError(f"Klasse '{klasse}' nicht gefunden. Vorhanden: {', '.join(vorhandene)}")
    knopf.first.click()

    warte_js = """([kl, tag]) => {
        const label = (document.querySelector('#selectedClassLabel')||{}).textContent || '';
        const upd = (document.querySelector('#updatedAt')||{}).textContent || '';
        const datum = (document.querySelector('#planDateInput')||{}).value || '';
        const list = document.querySelector('#planList');
        return label.toLowerCase().includes(kl.toLowerCase())
            && !/Lädt/i.test(upd)
            && (!tag || datum === tag)
            && list && list.children.length > 0;
    }"""
    # Erst warten, bis die Klasse geladen ist (Seite springt nach 12 Uhr evtl. auf morgen)
    page.wait_for_function(warte_js, arg=[klasse, ""], timeout=30000)

    # Auf "Heute" stellen und warten, bis der heutige Plan fertig geladen ist
    jetzt = datetime.now(BERLIN)
    heute_iso = jetzt.strftime("%Y-%m-%d")
    page.click("#todayButton")
    page.wait_for_timeout(500)
    page.wait_for_function(warte_js, arg=[klasse, heute_iso], timeout=30000)

    # Ab 15:30 Uhr und am Wochenende: einen Schultag weiter ("Weiter" überspringt Wochenenden/Ferientage)
    naechster = soll_naechster_tag(jetzt)
    if naechster:
        page.click("#nextDay")
        page.wait_for_timeout(500)
        page.wait_for_function(
            """([kl, tag]) => {
                const label = (document.querySelector('#selectedClassLabel')||{}).textContent || '';
                const upd = (document.querySelector('#updatedAt')||{}).textContent || '';
                const datum = (document.querySelector('#planDateInput')||{}).value || '';
                const list = document.querySelector('#planList');
                return label.toLowerCase().includes(kl.toLowerCase())
                    && !/Lädt/i.test(upd) && datum > tag
                    && list && list.children.length > 0;
            }""",
            arg=[klasse, heute_iso],
            timeout=30000,
        )
    page.wait_for_timeout(1500)  # kurz nachrendern lassen

    daten = page.evaluate(JS_AUSLESEN)

    # Prüfen, dass das richtige Datum eingestellt ist
    feld = daten.get("datum_feld")
    if feld and not naechster and feld != heute_iso:
        raise RuntimeError(f"Datum steht auf {feld}, nicht auf heute ({heute_iso}).")
    if feld and naechster and feld <= heute_iso:
        raise RuntimeError(f"Datum steht auf {feld}, sollte aber nach heute ({heute_iso}) liegen.")
    daten["ist_naechster_tag"] = naechster

    daten["stunden"] = [bewerte_stunde(s) for s in daten["stunden"]]
    return daten


# ---------------------------------------------------------------- Hauptprogramm
def main() -> int:
    lade_env_datei(HIER / "zugangsdaten.env")
    email = os.environ.get("RWG_EMAIL", "").strip()
    passwort = os.environ.get("RWG_PASSWORT", "")
    klasse = os.environ.get("KLASSE", "9c").strip() or "9c"
    sichtbar = "--sichtbar" in sys.argv

    jetzt = datetime.now(BERLIN)
    DEBUG_DIR.mkdir(exist_ok=True)
    PUBLIC_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not sichtbar)
        context = browser.new_context(
            locale="de-DE",
            timezone_id="Europe/Berlin",
            viewport={"width": 1400, "height": 1000},
        )
        page = context.new_page()
        # Falls die Seite ein Klassen-Passwort per prompt() abfragt: abbrechen statt hängen
        page.on("dialog", lambda d: d.dismiss())

        try:
            page.goto(PLAN_URL, wait_until="domcontentloaded", timeout=60000)
            anmelden_falls_noetig(page, email, passwort)
            daten = lese_plan(page, klasse)
        except Exception as fehler:
            try:
                page.screenshot(path=str(DEBUG_DIR / "fehler.png"), full_page=True)
                (DEBUG_DIR / "fehler.html").write_text(page.content(), encoding="utf-8")
            except Exception:
                pass
            print(f"FEHLER: {fehler}", file=sys.stderr)
            return 1
        finally:
            try:
                page.screenshot(path=str(DEBUG_DIR / "letzter_stand.png"), full_page=True)
            except Exception:
                pass
            browser.close()

    daten["klasse"] = klasse.upper()
    daten["abgerufen"] = jetzt.strftime("%d.%m.%Y, %H:%M")
    daten["abgerufen_iso"] = jetzt.isoformat()
    daten["datum_iso"] = daten.get("datum_feld") or jetzt.strftime("%Y-%m-%d")

    (PUBLIC_DIR / "plan.json").write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
    (PUBLIC_DIR / "index.html").write_text(baue_webseite(daten), encoding="utf-8")

    print(f"OK: {len(daten['stunden'])} Stunden für {daten['klasse']} am {daten['datum_text']} gespeichert.")
    if os.environ.get("CI"):  # GitHub-Logs sind öffentlich -> keine Plandetails ausgeben
        return 0
    for s in daten["stunden"]:
        print(f"  {s['stunde']:>2}. {s['status']:<9} {s['fach']:<8} {s['lehrer']:<6} {s['raum']:<6} {s['info']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
