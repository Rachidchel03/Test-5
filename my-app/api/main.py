# backend/main.py
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import json

from dotenv import load_dotenv

load_dotenv()  


from scraper import (
    fetch_pages_html_selenium,
    html_to_markdown_with_readability,
    create_dynamic_listing_model,
    create_listings_container_model,
    format_data,
    save_raw_data,
    save_formatted_data,
)
from API_omgevingsloket import get_rd_coordinates, search_plans, get_vlak_by_point

app = FastAPI()

# At top of file, after imports:
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000")
# split on comma if you want to allow multiple
origins = [o.strip() for o in FRONTEND_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    url: str
    pages: int = 1
    fields: list[str] = []

@app.post("/api/scrape")
async def scrape_data(req: ScrapeRequest):
    try:
        # ---- derive area + timestamp ----
        parsed = urlparse(req.url)
        qs = parse_qs(parsed.query)
        area = ""
        # funda selected_area param (JSON array or raw)
        if "selected_area" in qs:
            raw = qs["selected_area"][0]
            try:
                arr = json.loads(raw)
                area = arr[0] if isinstance(arr, list) and arr else raw
            except json.JSONDecodeError:
                area = raw.strip('[]"\'')
        # fallback: look for "gemeente-xxx" in path
        if not area:
            for seg in parsed.path.strip("/").split("/"):
                if seg.startswith("gemeente-"):
                    area = seg.split("-", 1)[1]
                    break
        # final fallback: first path segment
        if not area:
            parts = parsed.path.strip("/").split("/")
            if parts:
                area = parts[0]
        area_clean = area.replace(" ", "_")
        date_str = datetime.now().strftime("%Y%m%d")
        time_str = datetime.now().strftime("%H%M%S")
        ts = f"{area_clean}_{date_str}_{time_str}"
        # ----------------------------------

        # 1) scrape → markdown → structured listings
        html_pages = fetch_pages_html_selenium(req.url, pages=req.pages, fetch_all=False)
        combined_md = ""
        all_listings: list[dict] = []

        if req.fields:
            LM = create_dynamic_listing_model(req.fields)
            LC = create_listings_container_model(LM)
        else:
            LC = None

        for html in html_pages:
            md = html_to_markdown_with_readability(html)
            combined_md += md + "\n\n"
            if LC:
                res = format_data(md, LC)
                ls = res.dict().get("listings", [])
            else:
                ls = []
            all_listings.extend(ls)

        # 2) ENRICH each listing with bestemmingsplan
        for item in all_listings:
            addr = item.get("Adress") or item.get("address") or item.get("adres") or ""
            try:
                x, y = get_rd_coordinates(addr)
                plan_ids = search_plans(x, y)
                names: list[str] = []
                for pid in plan_ids:
                    vlakken = get_vlak_by_point(pid, x, y)
                    for vlak in vlakken:
                        naam = vlak.get("naam") or vlak.get("bestemmingshoofdgroep")
                        if naam:
                            names.append(naam)
                item["bestemmingsplan"] = sorted(set(names))
            except Exception:
                item["bestemmingsplan"] = []

        # 3) save raw + enriched Excel
        save_raw_data(combined_md, ts)
        container = {"listings": all_listings}
        # this writes to output/sorted_data_{ts}.xlsx
        save_formatted_data(container, ts)

        # immediately rename to output/{ts}.xlsx
        old_path = os.path.join("output", f"sorted_data_{ts}.xlsx")
        new_path = os.path.join("output", f"{ts}.xlsx")
        if os.path.exists(old_path):
            os.replace(old_path, new_path)

        return {"data": container, "timestamp": ts}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download-excel")
def download_excel(timestamp: str):
    # now looks for output/{timestamp}.xlsx
    path = os.path.join("output", f"{timestamp}.xlsx")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{timestamp}.xlsx",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
