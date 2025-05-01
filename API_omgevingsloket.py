# backend/api_omgevingsloket.py
import os
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import find_dotenv, load_dotenv
dotenvpath=find_dotenv()
load_dotenv(dotenvpath)

# Configuratie
RP_API_KEY=os.getenv("RP_API_KEY")
RP_BASE_URL = 'https://ruimte.omgevingswet.overheid.nl/ruimtelijke-plannen/api/opvragen/v4'
PDOK_URL = 'https://api.pdok.nl/bzk/locatieserver/search/v3_1/free'
HEADERS_RP = {
    'x-api-key': RP_API_KEY,
    'Content-Type': 'application/json',
    'Content-Crs': 'epsg:28992'
}
HEADERS_PDOK = {
    'Accept': 'application/json'
}

def get_rd_coordinates(address: str) -> tuple[float,float]:
    params = {
        'q': address,
        'fq': 'type:adres',
        'rows': 1,
        'fl': 'centroide_rd'
    }
    resp = requests.get(PDOK_URL, params=params, headers=HEADERS_PDOK)
    resp.raise_for_status()
    docs = resp.json().get('response', {}).get('docs', [])
    if not docs:
        raise HTTPException(status_code=404, detail=f"Geen coördinaten voor adres: {address}")
    point = docs[0]['centroide_rd']
    x_str, y_str = point.replace('POINT(', '').replace(')', '').split()
    return float(x_str), float(y_str)

def search_plans(x: float, y: float, margin: int = 25) -> list[str]:
    url = f"{RP_BASE_URL}/plannen/_zoek"
    params = {'planType': 'bestemmingsplan'}
    geo = {
      '_geo': {
        'intersects': {
          'type': 'Polygon',
          'coordinates': [[
            [x-margin, y-margin],
            [x+margin, y-margin],
            [x+margin, y+margin],
            [x-margin, y+margin],
            [x-margin, y-margin]
          ]]
        }
      }
    }
    resp = requests.post(url, headers=HEADERS_RP, params=params, json=geo)
    resp.raise_for_status()
    data = resp.json()
    plans = data.get('_embedded', {}).get('plannen') \
         or data.get('response', {}).get('docs', [])
    return [p.get('identificatie') or p.get('id') for p in plans]

def get_vlak_by_point(plan_id: str, x: float, y: float) -> list[dict]:
    url = f"{RP_BASE_URL}/plannen/{plan_id}/bestemmingsvlakken/_zoek"
    body = {'_geo': {'contains': {'type': 'Point', 'coordinates': [x, y]}}}
    resp = requests.post(url, headers=HEADERS_RP, json=body)
    resp.raise_for_status()
    return resp.json().get('_embedded', {}).get('bestemmingsvlakken', [])

router = APIRouter()

class BestemmingResponse(BaseModel):
    bestemming: list[str]

@router.get("/bestemming", response_model=BestemmingResponse)
def get_bestemming(address: str):
    """
    Haal per adres de bestemmingsplan-namen op.
    """
    try:
        x, y = get_rd_coordinates(address)
        plan_ids = search_plans(x, y)
        names: list[str] = []
        for pid in plan_ids:
            vlakken = get_vlak_by_point(pid, x, y)
            for vlak in vlakken:
                naam = vlak.get("naam") or vlak.get("bestemmingshoofdgroep")
                if naam:
                    names.append(naam)
        unique = sorted(set(names))
        return {"bestemming": unique}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
