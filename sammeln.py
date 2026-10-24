#!/usr/bin/env python3
"""Schritt 1: Feeds aus quellen.json abrufen, nach Steuer-Stichwörtern filtern
und das Ergebnis in sammlung.json schreiben. Nur Standardbibliothek nötig."""
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

BASIS = Path(__file__).parent
MAX_ALTER_TAGE = 2   # ältere Meldungen werden ignoriert
TIMEOUT = 20         # Sekunden pro Feed


def text_bereinigen(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def parse_datum(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)          # RSS: "Sat, 24 Oct 2026 08:00:00 +0200"
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))   # Atom
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def lokal(tag):
    return tag.rsplit("}", 1)[-1]


def kind_text(el, *namen):
    for k in el:
        if lokal(k.tag) in namen and (k.text or "").strip():
            return k.text
    return ""


def eintraege_parsen(xml_bytes):
    """Liest RSS 2.0 und Atom und liefert Titel, Link, Anriss und Datum."""
    root = ET.fromstring(xml_bytes)
    for el in root.iter():
        if lokal(el.tag) not in ("item", "entry"):
            continue
        link = kind_text(el, "link").strip()
        if not link:                              # Atom: <link href="...">
            for k in el:
                if lokal(k.tag) == "link" and k.get("href"):
                    link = k.get("href")
                    break
        yield {
            "titel": text_bereinigen(kind_text(el, "title")),
            "link": link,
            "anriss": text_bereinigen(kind_text(el, "description", "summary", "content"))[:600],
            "datum": parse_datum(kind_text(el, "pubDate", "published", "updated", "date")),
        }


def muster_bauen(stichwoerter):
    """Trifft Steuer, Einkommensteuer, Stromsteuer, Steuerschätzung usw.,
    aber nicht Steuerung oder Steuerrad."""
    teile = [r"\b" + re.escape(w) + r"\b" for w in stichwoerter]
    teile.append(r"\w*steuer(?!ung|bar|rad|ruder)\w*")
    return re.compile("|".join(teile), re.IGNORECASE)


def titel_schluessel(titel):
    return re.sub(r"[^a-z0-9äöüß]", "", titel.lower())


def main():
    konf = json.loads((BASIS / "quellen.json").read_text(encoding="utf-8"))
    muster = muster_bauen(konf["stichwoerter"])
    grenze = datetime.now(timezone.utc) - timedelta(days=MAX_ALTER_TAGE)
    treffer, links, titel_set = [], set(), set()

    for feed in konf["feeds"]:
        if not feed.get("url"):
            print(f"übersprungen (keine URL eingetragen): {feed['name']}")
            continue
        try:
            req = urllib.request.Request(feed["url"], headers={"User-Agent": "steuer-news/1.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as antwort:
                eintraege = list(eintraege_parsen(antwort.read()))
        except Exception as fehler:               # ein kaputter Feed soll nicht alles stoppen
            print(f"FEHLER bei {feed['name']}: {fehler}", file=sys.stderr)
            continue

        gefunden = 0
        for e in eintraege:
            if not e["titel"] or not e["link"]:
                continue
            if e["datum"] and e["datum"] < grenze:
                continue
            if not feed.get("alle_behalten") and not muster.search(e["titel"] + " " + e["anriss"]):
                continue
            schluessel = titel_schluessel(e["titel"])
            if e["link"] in links or schluessel in titel_set:
                continue                           # Duplikat
            links.add(e["link"])
            titel_set.add(schluessel)
            e["quelle"] = feed["name"]
            e["datum"] = e["datum"].isoformat() if e["datum"] else None
            treffer.append(e)
            gefunden += 1
        print(f"{feed['name']}: {len(eintraege)} Einträge, {gefunden} Treffer")

    treffer.sort(key=lambda e: e["datum"] or "", reverse=True)
    (BASIS / "sammlung.json").write_text(json.dumps(treffer, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(treffer)} Meldungen in sammlung.json gespeichert.")


if __name__ == "__main__":
    main()
