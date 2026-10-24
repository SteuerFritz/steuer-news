#!/usr/bin/env python3
"""Schritt 3: Aus zusammenfassungen.json die Seite ausgabe/index.html erzeugen."""
import html
import json
from datetime import date
from pathlib import Path

BASIS = Path(__file__).parent
THEMEN = ["Haushalt und Koalition", "Einkommensteuer", "Verbrauch und Energie",
          "Unternehmen und Wirtschaft", "Sonstiges"]
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]

VORLAGE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Steuer-Nachrichten Deutschland, %%DATUM%%</title>
<style>
:root{--bg:#f2f4f7;--card:#fff;--ink:#17202b;--mute:#5b6675;--line:#d6dce4;--accent:#1c58b8;--accent-ink:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#10151c;--card:#18202a;--ink:#e8edf3;--mute:#9aa6b5;--line:#2b3644;--accent:#6ea3f2;--accent-ink:#0b1320}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:46rem;margin:0 auto;padding:2rem 1.1rem 3rem}
h1,h2{font-family:Georgia,"Times New Roman",serif;line-height:1.2;margin:0}
h1{font-size:2.1rem}
.date{color:var(--mute);margin:.3rem 0 1.4rem}
.lead{background:var(--accent);color:var(--accent-ink);padding:1.4rem 1.4rem 1.2rem;border-radius:6px;margin-bottom:1.6rem}
.lead h2{font-size:1.55rem;margin-bottom:.5rem}
.lead p{margin:0 0 .6rem}
.lead a{color:inherit}
.chips{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1.4rem}
.chips button{font:inherit;font-size:.92rem;padding:.35rem .85rem;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;cursor:pointer}
.chips button[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.chips button:focus-visible,a:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
section{margin-bottom:1.8rem}
section[hidden]{display:none}
h2.cat{font-size:1.3rem;padding-bottom:.4rem;border-bottom:2px solid var(--ink);margin-bottom:.2rem}
article{padding:.9rem 0;border-bottom:1px solid var(--line)}
article h3{font-size:1.05rem;margin:0 0 .2rem}
article p{margin:0 0 .3rem}
.src{font-size:.85rem;color:var(--mute)}
.src a{color:var(--mute)}
footer{color:var(--mute);font-size:.88rem;border-top:1px solid var(--line);padding-top:1rem}
</style>
</head>
<body>
<main>
<header>
<h1>Steuer-Nachrichten Deutschland</h1>
<p class="date">%%DATUM%%</p>
</header>
%%AUFMACHER%%
%%CHIPS%%
%%ABSCHNITTE%%
<footer>
Diese Seite wird automatisch erstellt. Die Zusammenfassungen schreibt eine KI und stützt sich dabei nur auf Titel und Anriss der verlinkten Meldungen. Sie können Fehler enthalten, maßgeblich ist die Quelle. Es handelt sich um Nachrichten, nicht um Steuerberatung.
</footer>
</main>
<script>
const btns=document.querySelectorAll('.chips button'),secs=document.querySelectorAll('section[data-c]');
btns.forEach(b=>b.addEventListener('click',()=>{
btns.forEach(x=>x.setAttribute('aria-pressed',x===b));
secs.forEach(s=>s.hidden=b.dataset.f!=='alle'&&s.dataset.c!==b.dataset.f);
}));
</script>
</body>
</html>
"""


def esc(s):
    return html.escape(s or "", quote=True)


def sicherer_link(url):
    return url if url.startswith(("http://", "https://")) else "#"


def quelle(m):
    return f'<span class="src"><a href="{esc(sicherer_link(m["link"]))}" rel="noopener">{esc(m["quelle"])}</a></span>'


def main():
    pfad = BASIS / "zusammenfassungen.json"
    meldungen = json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else []
    heute = date.today()
    datum = f"{WOCHENTAGE[heute.weekday()]}, {heute.day}. {MONATE[heute.month - 1]} {heute.year}"

    if not meldungen:
        aufmacher = '<div class="lead"><h2>Heute keine passenden Meldungen</h2><p>In den abgefragten Quellen wurde nichts zu deutschen Steuerthemen gefunden.</p></div>'
        chips, abschnitte = "", ""
    else:
        erste, rest = meldungen[0], meldungen[1:]
        aufmacher = (f'<div class="lead"><h2>{esc(erste["titel"])}</h2><p>{esc(erste["zusammenfassung"])}</p>'
                     f'{quelle(erste)}</div>')
        gruppen = {t: [m for m in rest if m["thema"] == t] for t in THEMEN}
        gruppen = {t: ms for t, ms in gruppen.items() if ms}
        knoepfe = ['<button aria-pressed="true" data-f="alle">Alle</button>']
        abschnitte = []
        for i, (thema, ms) in enumerate(gruppen.items()):
            kennung = f"t{i}"
            knoepfe.append(f'<button aria-pressed="false" data-f="{kennung}">{esc(thema)}</button>')
            artikel = "".join(
                f'<article><h3>{esc(m["titel"])}</h3><p>{esc(m["zusammenfassung"])}</p>{quelle(m)}</article>'
                for m in ms)
            abschnitte.append(f'<section data-c="{kennung}"><h2 class="cat">{esc(thema)}</h2>{artikel}</section>')
        chips = ('<nav class="chips" aria-label="Themen filtern">' + "".join(knoepfe) + "</nav>") if gruppen else ""
        abschnitte = "\n".join(abschnitte)

    seite = (VORLAGE.replace("%%DATUM%%", datum).replace("%%AUFMACHER%%", aufmacher)
             .replace("%%CHIPS%%", chips).replace("%%ABSCHNITTE%%", abschnitte))
    ziel = BASIS / "ausgabe"
    ziel.mkdir(exist_ok=True)
    (ziel / "index.html").write_text(seite, encoding="utf-8")
    print(f"ausgabe/index.html erstellt ({len(meldungen)} Meldungen).")


if __name__ == "__main__":
    main()
