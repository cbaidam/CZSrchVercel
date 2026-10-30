import json
import os
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

app = FastAPI()

PAGES_PATH = os.path.join(os.path.dirname(__file__), "pages.jsonl")


def nacti_stranky():
    """Načte naindexované stránky z pages.jsonl (jeden JSON objekt na řádek)."""
    stranky = []
    if os.path.exists(PAGES_PATH):
        with open(PAGES_PATH, "r", encoding="utf-8") as f:
            for radek in f:
                radek = radek.strip()
                if not radek:
                    continue
                try:
                    stranky.append(json.loads(radek))
                except json.JSONDecodeError:
                    continue
    return stranky


# Načteme jednou při startu funkce (ne znovu při každém requestu)
DATABAZE_WEBU = nacti_stranky()


@app.get("/")
def domovska_stranka(q: str = Query(default="")):
    vysledky = []
    if q:
        vyraz = q.lower()
        for web in DATABAZE_WEBU:
            if vyraz in web.get("title", "").lower() or vyraz in web.get("text", "").lower():
                vysledky.append(web)

    html_obsah = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Czechia Search</title>
        <style>
            body {{ font-family: sans-serif; background: #121212; color: #e0e0e0; max-width: 800px; margin: 40px auto; padding: 0 20px; }}
            h1 {{ color: #a855f7; text-align: center; }}
            .search-box {{ text-align: center; margin-bottom: 10px; }}
            input[type="text"] {{ width: 70%; padding: 12px; background: #222; border: 2px solid #a855f7; color: #fff; border-radius: 6px; font-size: 16px; }}
            button {{ padding: 12px 20px; background: #a855f7; border: none; color: white; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; }}
            button:hover {{ background: #9333ea; }}
            .pocet {{ text-align: center; color: #555; font-size: 12px; margin-bottom: 25px; }}
            .vysledek {{ background: #1e1e1e; padding: 20px; margin-bottom: 15px; border-radius: 8px; border-left: 4px solid #a855f7; }}
            .vysledek a {{ color: #c084fc; font-size: 18px; text-decoration: none; font-weight: bold; }}
            .vysledek a:hover {{ text-decoration: underline; }}
            .vysledek .url {{ color: #22c55e; font-size: 12px; margin: 4px 0; }}
            .vysledek .desc {{ color: #aaaaaa; font-size: 14px; line-height: 1.4; }}
            .no-results {{ text-align: center; color: #888; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <h1>🦁 Czechia Search</h1>
        <div class="search-box">
            <form action="/" method="get">
                <input type="text" name="q" value="{q}" placeholder="Hledat bez sledování a kravin..." required>
                <button type="submit">Hledat</button>
            </form>
        </div>
        <div class="pocet">Index: {len(DATABAZE_WEBU)} stránek</div>
        <div>
    """

    if q:
        if vysledky:
            for res in vysledky:
                html_obsah += f"""
                <div class="vysledek">
                    <a href="{res.get('url', '')}" target="_blank">{res.get('title', '')}</a>
                    <div class="url">{res.get('url', '')}</div>
                    <div class="desc">{res.get('text', '')}</div>
                </div>
                """
        else:
            html_obsah += f'<div class="no-results">Pro výraz "{q}" nebylo nic nalezeno.</div>'

    html_obsah += """
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_obsah)
