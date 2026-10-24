#!/usr/bin/env python3
"""Schritt 2: Jede Meldung aus sammlung.json von Claude prüfen und zusammenfassen
lassen. Ergebnis: zusammenfassungen.json. Nur Standardbibliothek nötig.

Voraussetzung: Umgebungsvariable ANTHROPIC_API_KEY ist gesetzt."""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASIS = Path(__file__).parent
MODELL = os.environ.get("CLAUDE_MODELL", "claude-haiku-5-5")
MAX_ARTIKEL = 40
THEMEN = ["Haushalt und Koalition", "Einkommensteuer", "Verbrauch und Energie",
          "Unternehmen und Wirtschaft", "Sonstiges"]

SYSTEM = f"""Du prüfst Nachrichtenmeldungen für eine Seite mit deutschen Steuer-Nachrichten.
Du bekommst nur Titel, Anriss und Quelle einer Meldung.

Antworte ausschließlich mit einem JSON-Objekt, ohne weiteren Text:
{{"relevant": true oder false,
 "thema": eines von {json.dumps(THEMEN, ensure_ascii=False)},
 "titel": "kurzer, sachlicher Titel in eigenen Worten",
 "zusammenfassung": "zwei bis drei Sätze in eigenen Worten"}}

Regeln:
- relevant ist nur true, wenn die Meldung Deutschland betrifft UND im Kern um Steuern, Abgaben oder Steuerpolitik geht. Ausländische Steuerthemen und Zufallstreffer (etwa "Steuerung" im Sinne von Lenkung) sind nicht relevant.
- Verwende ausschließlich Informationen aus Titel und Anriss. Erfinde keine Zahlen, Namen oder Hintergründe.
- Gibt der Anriss zu wenig her, fasse nur das zusammen, was da steht, und halte die Zusammenfassung kurz.
- Schreibe in eigenen Worten und übernimm keine Sätze wörtlich."""


def frage_claude(nutzertext, api_key):
    daten = json.dumps({
        "model": MODELL,
        "max_tokens": 500,
        "system": SYSTEM,
        "messages": [{"role": "user", "content": nutzertext}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=daten,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
    )
    for versuch in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as antwort:
                return json.loads(antwort.read())["content"][0]["text"]
        except urllib.error.HTTPError as fehler:
            if fehler.code in (429, 500, 529) and versuch < 2:
                time.sleep(5 * (versuch + 1))
                continue
            raise
    return ""


def json_aus_text(text):
    """Holt das JSON-Objekt aus der Antwort, auch wenn Code-Zäune darum stehen."""
    anfang, ende = text.find("{"), text.rfind("}")
    if anfang == -1 or ende == -1:
        raise ValueError("kein JSON in der Antwort")
    return json.loads(text[anfang:ende + 1])


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY ist nicht gesetzt.")
    meldungen = json.loads((BASIS / "sammlung.json").read_text(encoding="utf-8"))[:MAX_ARTIKEL]
    ergebnis = []
    for m in meldungen:
        nutzertext = f"Quelle: {m['quelle']}\nTitel: {m['titel']}\nAnriss: {m['anriss'] or '(kein Anriss vorhanden)'}"
        try:
            antwort = json_aus_text(frage_claude(nutzertext, api_key))
        except Exception as fehler:
            print(f"übersprungen ({fehler}): {m['titel'][:60]}", file=sys.stderr)
            continue
        if antwort.get("relevant") is not True:
            continue
        thema = antwort.get("thema") if antwort.get("thema") in THEMEN else "Sonstiges"
        ergebnis.append({
            "titel": antwort.get("titel") or m["titel"],
            "zusammenfassung": antwort.get("zusammenfassung", ""),
            "thema": thema,
            "link": m["link"],
            "quelle": m["quelle"],
            "datum": m["datum"],
        })
    (BASIS / "zusammenfassungen.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(ergebnis)} von {len(meldungen)} Meldungen als relevant eingestuft.")


if __name__ == "__main__":
    main()
