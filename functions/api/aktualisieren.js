// Cloudflare Pages Function: /api/aktualisieren
//   POST -> startet den GitHub-Workflow "plan.yml" (wenn er nicht gerade schon läuft)
//   GET  -> Status des letzten Laufs (für die Fortschrittsanzeige auf der Seite)
// Benötigt die Cloudflare-Secrets GH_TOKEN und GH_REPO (setzt der Workflow automatisch).

const WORKFLOW = "plan.yml";
const SPERRE_MS = 2 * 60 * 1000; // frühestens 2 Minuten nach dem letzten Start erneut starten

function gh(env, pfad, init = {}) {
  return fetch(`https://api.github.com/repos/${env.GH_REPO}/actions/workflows/${WORKFLOW}${pfad}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "vertretungsplan-knopf",
      ...(init.headers || {}),
    },
  });
}

function antwort(daten, status = 200) {
  return new Response(JSON.stringify(daten), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

async function letzterLauf(env) {
  const r = await gh(env, "/runs?per_page=1");
  if (!r.ok) throw new Error(`GitHub antwortet ${r.status}`);
  const run = (await r.json()).workflow_runs?.[0];
  if (!run) return null;
  return { status: run.status, ergebnis: run.conclusion, gestartet: run.created_at };
}

export async function onRequestGet({ env }) {
  try {
    return antwort({ lauf: await letzterLauf(env) });
  } catch (e) {
    return antwort({ fehler: String(e.message || e) }, 500);
  }
}

export async function onRequestPost({ env }) {
  if (!env.GH_TOKEN || !env.GH_REPO) {
    return antwort({ fehler: "Knopf ist noch nicht eingerichtet (GH_TOKEN fehlt)." }, 500);
  }
  try {
    const lauf = await letzterLauf(env);
    const laeuft = lauf && lauf.status !== "completed";
    const geradeErst = lauf && Date.now() - Date.parse(lauf.gestartet) < SPERRE_MS;
    if (laeuft || geradeErst) {
      return antwort({ status: "laeuft_schon", seit: lauf.gestartet });
    }
    const r = await gh(env, "/dispatches", {
      method: "POST",
      body: JSON.stringify({ ref: "main" }),
      headers: { "Content-Type": "application/json" },
    });
    if (r.status !== 204) {
      return antwort({ fehler: `Start fehlgeschlagen (GitHub ${r.status})` }, 502);
    }
    return antwort({ status: "gestartet", seit: new Date().toISOString() });
  } catch (e) {
    return antwort({ fehler: String(e.message || e) }, 500);
  }
}
