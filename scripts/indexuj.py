"""
Jednoduchy crawler. Jednou denne ho spusti GitHub Actions (viz
.github/workflows/index.yml), ktery projde seznam stranek v SEED_URLS,
stahne je, vytahne titulek + kratky text a ulozi do api/pages.jsonl.
Ten pak cte vyhledavac v api/main.py.
"""
import json
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Odkud se zacina crawlovat - klidne si doplň vlastni stranky.
SEED_URLS = [
    "https://cs.wikipedia.org/wiki/Hlavn%C3%AD_strana",
    "https://www.root.cz/",
    "https://www.python.org/",
]

MAX_STRANEK = 300   # kolik stranek max naindexovat (at to nebezi vecne)
MAX_HLOUBKA = 2     # kolik "kliknuti" od seedu se crawler smi vzdalit
TIMEOUT = 8         # vterin na jeden pozadavek

VYSTUPNI_SOUBOR = Path(__file__).resolve().parent.parent / "api" / "pages.jsonl"
HEADERS = {"User-Agent": "CzechiaSearchBot/1.0"}


def ziskej_text(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()[:300]
    p = soup.find("p")
    if p:
        return p.get_text(strip=True)[:300]
    return ""


def crawluj():
    navstiveno = set()
    fronta = [(url, 0) for url in SEED_URLS]
    vysledky = []

    while fronta and len(vysledky) < MAX_STRANEK:
        url, hloubka = fronta.pop(0)
        if url in navstiveno:
            continue
        navstiveno.add(url)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        titulek = soup.title.string.strip() if soup.title and soup.title.string else url
        text = ziskej_text(soup)

        vysledky.append({"title": titulek, "url": url, "text": text})
        print(f"[{len(vysledky)}] {url}")

        if hloubka < MAX_HLOUBKA:
            for a in soup.find_all("a", href=True):
                odkaz = urljoin(url, a["href"])
                if urlparse(odkaz).scheme in ("http", "https") and odkaz not in navstiveno:
                    fronta.append((odkaz, hloubka + 1))

        time.sleep(0.5)  # slusnost k serverum

    return vysledky


def uloz(vysledky):
    VYSTUPNI_SOUBOR.parent.mkdir(parents=True, exist_ok=True)
    with open(VYSTUPNI_SOUBOR, "w", encoding="utf-8") as f:
        for radek in vysledky:
            f.write(json.dumps(radek, ensure_ascii=False) + "\n")
    print(f"Hotovo: {len(vysledky)} stranek ulozeno do {VYSTUPNI_SOUBOR}")


if __name__ == "__main__":
    data = crawluj()
    uloz(data)
