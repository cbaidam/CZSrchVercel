"""
Jednoduchy crawler. Jednou denne ho spusti GitHub Actions (viz
.github/workflows/index.yml), ktery projde seznam stranek v SEED_URLS,
stahne je, vytahne titulek + kratky text a ulozi do api/pages.jsonl.
Ten pak cte vyhledavac v api/main.py.
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, urlunparse

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

# Crawler se nesmi vzdalit mimo domeny, odkud zacal (jinak za chvili
# konci na stovkach jazykovych mutaci Wikipedie atd.)
POVOLENE_DOMENY = {urlparse(u).netloc for u in SEED_URLS}

# Kousky URL, ktere znamenaji "neni to clanek, je to admin/meta stranka"
# (editace, historie, specialni stranky, prihlaseni, kategorie...)
VYLOUCENE_VZORY = [
    "action=edit", "action=history", "action=info", "redlink=1",
    "oldid=", "UploadWizard", "DownloadAsPdf", "useparsoid=",
    "/w/index.php",
    "Special:", "Speciální:", "Speciáln%C3%AD:",
    "Help:", "Nápověda:", "N%C3%A1pov%C4%9Bda:",
    "Talk:", "Diskuse:",
    "Category:", "Kategorie:",
    "Portal:", "Portál:", "Port%C3%A1l:",
    "File:", "Soubor:",
    "Template:", "Šablona:",
    "Module:", "Modul:",
    "MediaWiki:",
]


def normalizuj(url: str) -> str:
    """Odstrani #fragment, aby stejna stranka s ruznou kotvou nebyla brana jako dve ruzne."""
    rozparsovano = urlparse(url)
    return urlunparse(rozparsovano._replace(fragment=""))


def je_zajimava(url: str) -> bool:
    rozparsovano = urlparse(url)
    if rozparsovano.scheme not in ("http", "https"):
        return False
    if rozparsovano.netloc not in POVOLENE_DOMENY:
        return False
    # Porovnavame dekodovanou verzi, protoze odkazy na wiki byvaji
    # URL-encodovane (napr. "Speci%C3%A1ln%C3%AD:" misto "Speciální:")
    dekodovana_url = unquote(url)
    for vzor in VYLOUCENE_VZORY:
        if vzor in url or vzor in dekodovana_url:
            return False
    return True


def ziskej_text(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        text = meta["content"]
    else:
        p = soup.find("p")
        text = p.get_text(separator=" ", strip=True) if p else ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]


def crawluj():
    navstiveno = set()
    fronta = [(normalizuj(url), 0) for url in SEED_URLS]
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

        # Pokud stranka presmerovala (napr. "Nahodna stranka" -> konkretni
        # clanek), ulozime URL konecneho clanku, ne URL presmerovani.
        konecna_url = normalizuj(resp.url)
        if konecna_url in navstiveno and konecna_url != url:
            continue
        navstiveno.add(konecna_url)

        if not je_zajimava(konecna_url):
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        titulek = soup.title.string.strip() if soup.title and soup.title.string else konecna_url
        text = ziskej_text(soup)

        vysledky.append({"title": titulek, "url": konecna_url, "text": text})
        print(f"[{len(vysledky)}] {konecna_url}")

        if hloubka < MAX_HLOUBKA:
            for a in soup.find_all("a", href=True):
                odkaz = normalizuj(urljoin(url, a["href"]))
                if je_zajimava(odkaz) and odkaz not in navstiveno:
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
