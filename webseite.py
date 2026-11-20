"""Baut aus den ausgelesenen Plandaten eine einzelne, eigenständige HTML-Seite."""

from html import escape


def _e(wert) -> str:
    return escape(str(wert or ""))


def _stunde_html(s: dict) -> str:
    status = s.get("status", "normal")
    badge = {
        "ausfall": '<span class="badge badge-aus">Ausfall</span>',
        "aenderung": '<span class="badge badge-aend">Geändert</span>',
    }.get(status, "")

    fach = s.get("fach") or ""
    if status == "ausfall" and fach.lower() == "ausfall":
        fach = "–"

    details = []
    if s.get("lehrer"):
        cls = " geaendert" if s.get("lehrer_geaendert") else ""
        details.append(f'<span class="det{cls}">👤 {_e(s["lehrer"])}</span>')
    if s.get("raum"):
        cls = " geaendert" if s.get("raum_geaendert") else ""
        details.append(f'<span class="det{cls}">🚪 {_e(s["raum"])}</span>')
    if s.get("kurs"):
        details.append(f'<span class="det">{_e(s["kurs"])}</span>')

    info = f'<p class="info">{_e(s["info"])}</p>' if s.get("info") else ""
    fach_cls = " geaendert" if s.get("fach_geaendert") and status != "ausfall" else ""

    return f"""
    <article class="stunde st-{status}">
      <div class="nr">{_e(s.get("stunde"))}.</div>
      <div class="inhalt">
        <div class="kopf">
          <span class="fach{fach_cls}">{_e(fach)}</span>
          {badge}
          <span class="zeit">{_e(s.get("zeit"))}</span>
        </div>
        <div class="details">{"".join(details)}</div>
        {info}
      </div>
    </article>"""


def baue_webseite(d: dict) -> str:
    stunden = d.get("stunden", [])
    n_aus = sum(1 for s in stunden if s["status"] == "ausfall")
    n_aend = sum(1 for s in stunden if s["status"] == "aenderung")
    n_unterricht = len(stunden) - n_aus

    if stunden:
        liste = "".join(_stunde_html(s) for s in stunden)
    else:
        liste = f'<div class="leer">{_e(d.get("leer_text") or "Für heute liegt kein Plan vor.")}</div>'

    extra = ""
    for karte in d.get("info_karten", []):
        zeilen = "".join(f"<li>{_e(z)}</li>" for z in karte.get("zeilen", []))
        extra += f'<section class="karte"><h2>{_e(karte.get("titel"))}</h2><ul>{zeilen}</ul></section>'

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta http-equiv="refresh" content="900">
<title>Plan {_e(d.get("klasse"))}</title>
<style>
  :root {{
    --bg: #f6f4f1; --card: #ffffff; --text: #1d1b19; --muted: #6b6560; --line: #e3ded8;
    --accent: #b5532a;
    --aus-bg: #fdecea; --aus-line: #d93025; --aus-text: #b3261e;
    --aend-bg: #fff6e0; --aend-line: #e3a008; --aend-text: #8a5a00;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #161412; --card: #211e1b; --text: #f1ece6; --muted: #a59d95; --line: #35302b;
      --accent: #e08a5f;
      --aus-bg: #3a1d1b; --aus-line: #ef5350; --aus-text: #ff8a80;
      --aend-bg: #3a2f14; --aend-line: #f2b632; --aend-text: #f7cf6b;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--text);
         font: 17px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 680px; margin: 0 auto; padding: 20px 16px 40px; }}
  .klasse {{ font-size: 13px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); font-weight: 600; }}
  h1 {{ margin: 2px 0 6px; font-size: 26px; color: var(--accent); }}
  .stand {{ color: var(--muted); font-size: 14px; }}
  .warnung {{ display: none; margin: 14px 0 0; padding: 12px 14px; border-radius: 10px;
             background: var(--aus-bg); color: var(--aus-text); border: 1px solid var(--aus-line); font-weight: 600; }}
  .summe {{ display: flex; gap: 8px; margin: 16px 0; flex-wrap: wrap; }}
  .chip {{ background: var(--card); border: 1px solid var(--line); border-radius: 999px; padding: 6px 12px; font-size: 15px; }}
  .chip b {{ font-size: 17px; }}
  .chip.aus b {{ color: var(--aus-text); }}
  .chip.aend b {{ color: var(--aend-text); }}
  .stunde {{ display: flex; gap: 12px; background: var(--card); border: 1px solid var(--line);
            border-left: 6px solid var(--line); border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; }}
  .st-ausfall {{ background: var(--aus-bg); border-left-color: var(--aus-line); }}
  .st-aenderung {{ background: var(--aend-bg); border-left-color: var(--aend-line); }}
  .nr {{ font-size: 22px; font-weight: 700; color: var(--accent); min-width: 30px; }}
  .inhalt {{ flex: 1; min-width: 0; }}
  .kopf {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
  .fach {{ font-size: 20px; font-weight: 700; }}
  .st-ausfall .fach {{ text-decoration: line-through; color: var(--muted); }}
  .zeit {{ margin-left: auto; color: var(--muted); font-size: 14px; white-space: nowrap; }}
  .badge {{ font-size: 13px; font-weight: 700; padding: 2px 9px; border-radius: 999px; color: #fff; }}
  .badge-aus {{ background: var(--aus-line); }}
  .badge-aend {{ background: var(--aend-line); color: #2a1d00; }}
  .details {{ display: flex; gap: 14px; flex-wrap: wrap; margin-top: 4px; color: var(--muted); font-size: 15px; }}
  .geaendert {{ color: var(--aend-text); font-weight: 700; }}
  .info {{ margin: 6px 0 0; font-size: 15px; }}
  .leer, .karte {{ background: var(--card); border: 1px dashed var(--line); border-radius: 12px; padding: 18px; }}
  .leer {{ text-align: center; color: var(--muted); }}
  .karte {{ border-style: solid; margin-top: 14px; }}
  .karte h2 {{ margin: 0 0 6px; font-size: 16px; }}
  .karte ul {{ margin: 0; padding-left: 18px; }}
  footer {{ margin-top: 24px; color: var(--muted); font-size: 13px; text-align: center; }}
  .knopf {{ display: block; width: 100%; margin: 16px 0 0; padding: 14px; font: inherit; font-weight: 700;
           font-size: 18px; color: #fff; background: var(--accent); border: 0; border-radius: 12px; cursor: pointer; }}
  .knopf:disabled {{ opacity: .6; cursor: wait; }}
  .knopf-info {{ min-height: 1.4em; margin-top: 6px; text-align: center; color: var(--muted); font-size: 14px; }}
</style>
</head>
<body>
<main>
  <div class="klasse">Vertretungsplan · Klasse {_e(d.get("klasse"))}</div>
  <h1>{_e(d.get("datum_text"))}</h1>
  <div class="stand">Abgerufen: {_e(d.get("abgerufen"))} Uhr · Stand Schule: {_e(str(d.get("aktualisiert") or "").replace("aktualisiert", "").strip())}</div>
  <div class="warnung" id="warnung">⚠️ Achtung: Dieser Plan ist nicht von heute. Tippe auf „Aktualisieren“.</div>
  <button class="knopf" id="knopf" type="button">↻ Aktualisieren</button>
  <div class="knopf-info" id="knopfInfo"></div>

  <div class="summe">
    <span class="chip"><b>{n_unterricht}</b> Stunden Unterricht</span>
    <span class="chip aus"><b>{n_aus}</b> Ausfall</span>
    <span class="chip aend"><b>{n_aend}</b> Änderungen</span>
  </div>

  {liste}
  {extra}

  <footer>Wird an Schultagen automatisch alle 30 Minuten aktualisiert – oder sofort mit dem Knopf oben.</footer>
</main>
<script>
  (function () {{
    var planTag = "{_e(d.get("datum_iso"))}";
    var j = new Date();
    var heute = j.getFullYear() + "-" + String(j.getMonth() + 1).padStart(2, "0") + "-" + String(j.getDate()).padStart(2, "0");
    if (planTag !== heute) document.getElementById("warnung").style.display = "block";
  }})();

  (function () {{
    var knopf = document.getElementById("knopf");
    var info = document.getElementById("knopfInfo");
    var API = "/api/aktualisieren";

    function fertig(text) {{ knopf.disabled = false; knopf.textContent = "↻ Aktualisieren"; info.textContent = text; }}

    function warte(seit, start) {{
      if (Date.now() - start > 5 * 60 * 1000) return fertig("Dauert zu lange – bitte später nochmal versuchen.");
      fetch(API, {{ cache: "no-store" }}).then(function (r) {{ return r.json(); }}).then(function (d) {{
        var l = d.lauf;
        var neu = l && Date.parse(l.gestartet) >= Date.parse(seit) - 15000;
        if (neu && l.status === "completed") {{
          if (l.ergebnis === "success") {{
            info.textContent = "Fertig! Seite wird neu geladen …";
            setTimeout(function () {{ location.replace(location.pathname + "?t=" + Date.now()); }}, 1500);
          }} else {{
            fertig("Abruf hat nicht geklappt. Bitte später nochmal versuchen.");
          }}
          return;
        }}
        setTimeout(function () {{ warte(seit, start); }}, 5000);
      }}).catch(function () {{ setTimeout(function () {{ warte(seit, start); }}, 5000); }});
    }}

    knopf.addEventListener("click", function () {{
      knopf.disabled = true;
      knopf.textContent = "Wird abgerufen …";
      info.textContent = "Das dauert etwa 1–2 Minuten.";
      fetch(API, {{ method: "POST" }}).then(function (r) {{ return r.json(); }}).then(function (d) {{
        if (d.fehler) return fertig("Fehler: " + d.fehler);
        if (d.status === "laeuft_schon") info.textContent = "Wird gerade schon abgerufen – einen Moment …";
        warte(d.seit, Date.now());
      }}).catch(function () {{ fertig("Keine Verbindung – bitte nochmal versuchen."); }});
    }});
  }})();
</script>
</body>
</html>
"""
