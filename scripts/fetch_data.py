"""Fetch LotLens source data for the demo towns and build a lot-level table.

Downloads (into data/raw/<town>/):
  - MassGIS L3 property tax parcels + assessor table (per-town shapefile zip)
  - MassDEP POTW sewer service areas (clipped to the town)
  - MassDEP community water service areas (clipped to the town)
  - MassGIS 2-D building structures (by TOWN_ID)

Writes (into data/processed/):
  - <town>_lots.geojson   one feature per residential parcel, with Q7 checks
  - towns_summary.json    counts per town

Owner names are dropped on load and never written out.
Zoning minimums and frontage are NOT computed yet (see README).

Usage:  .venv/bin/python scripts/fetch_data.py [town ...]
"""

from __future__ import annotations

import json
import math
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

# MassGIS town IDs (from the MassGIS parcel download links table).
TOWNS = {
    "lexington": 155,
    "newton": 207,
    "needham": 199,
    "wellesley": 317,
    "framingham": 100,
    "quincy": 243,
}

PARCEL_ZIP = "http://download.massgis.digital.mass.gov/shapefiles/l3parcels/L3_SHP_M{id:03d}_{name}.zip"
AGOL = "https://arcgisserver.digital.mass.gov/arcgisserver/rest/services/AGOL"
SEWER_URL = f"{AGOL}/DEP_SEWER_SERVICE_AREAS/FeatureServer/2"        # POTW (public) sewer
WATER_URL = f"{AGOL}/DEP_PWS_WATER_SERVICE_AREAS/FeatureServer/2"    # community (public) water
BLDG_URL = "https://services1.arcgis.com/hGdibHYSPO59RG1h/arcgis/rest/services/Building_Structures/FeatureServer/0"

MA_CRS = "EPSG:26986"   # MA State Plane (meters), MassGIS native
SQFT_PER_M2 = 10.7639
Q7_MIN_SQFT = 5000

# Assessor use codes (first 3 digits): 101 single-family; 130/131 vacant
# developable / potentially developable residential land. Verify against the
# MassGIS parcel documentation before relying on them.
USE_KEEP = {"101": "single_family", "130": "vacant_developable", "131": "vacant_potential"}
OWNER_COLS = {"OWNER1", "OWN_ADDR", "OWN_CITY", "OWN_STATE", "OWN_ZIP", "OWN_CO", "LS_BOOK", "LS_PAGE"}

session = requests.Session()
session.headers["User-Agent"] = "LotLens-hackathon/0.1"


def download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with session.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.rename(dest)
    return dest


def query_layer(url: str, *, where: str = "1=1", bbox=None) -> gpd.GeoDataFrame:
    """Page through an ArcGIS FeatureServer layer and return a GeoDataFrame in MA_CRS."""
    params = {
        "where": where, "outFields": "*", "f": "geojson",
        "outSR": 4326, "resultRecordCount": 2000,
    }
    if bbox is not None:  # (minx, miny, maxx, maxy) in EPSG:4326
        params.update({
            "geometry": ",".join(map(str, bbox)), "geometryType": "esriGeometryEnvelope",
            "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
        })
    feats, offset = [], 0
    while True:
        r = session.get(f"{url}/query", params={**params, "resultOffset": offset}, timeout=120)
        r.raise_for_status()
        page = r.json()
        if "error" in page:
            raise RuntimeError(f"{url}: {page['error']}")
        batch = page.get("features", [])
        feats += batch
        if len(batch) < params["resultRecordCount"] and not page.get("exceededTransferLimit"):
            break
        offset += len(batch)
    if not feats:
        return gpd.GeoDataFrame(geometry=[], crs=MA_CRS)
    return gpd.GeoDataFrame.from_features(feats, crs="EPSG:4326").to_crs(MA_CRS)


def cached_layer(path: Path, **kw) -> gpd.GeoDataFrame:
    if path.exists():
        return gpd.read_file(path)
    gdf = query_layer(**kw)
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GeoJSON")
    return gdf.to_crs(MA_CRS)


def load_parcels(name: str, town_id: int) -> gpd.GeoDataFrame:
    zpath = download(PARCEL_ZIP.format(id=town_id, name=name.upper()), RAW / name / "parcels.zip")
    folder = RAW / name / "parcels"
    if not folder.exists():
        with zipfile.ZipFile(zpath) as z:
            z.extractall(folder)
    # Names look like M155TaxPar.shp or M155TaxPar_CY26_FY26.shp.
    shp = next(folder.rglob(f"M{town_id:03d}TaxPar*.shp"))
    dbf = next(folder.rglob(f"M{town_id:03d}Assess*.dbf"))

    parcels = gpd.read_file(shp).to_crs(MA_CRS)
    assess = gpd.read_file(dbf, ignore_geometry=True)
    assess = assess.drop(columns=[c for c in assess.columns if c in OWNER_COLS])
    # Several assessor rows can share one LOC_ID (condos); keep the first.
    assess = assess.drop_duplicates("LOC_ID")
    return parcels.merge(assess, on="LOC_ID", how="left")


def lot_sqft(row) -> float:
    size, units = row.get("LOT_SIZE"), str(row.get("LOT_UNITS") or "").upper()
    if pd.notna(size) and size and size > 0:
        if units.startswith("A"):
            return float(size) * 43560
        if units.startswith("S"):
            return float(size)
    return row["poly_sqft"]


def build_town(name: str, town_id: int) -> dict:
    print(f"[{name}] parcels", flush=True)
    gdf = load_parcels(name, town_id)
    bbox = tuple(gdf.to_crs(4326).total_bounds)

    print(f"[{name}] sewer / water / buildings", flush=True)
    sewer = cached_layer(RAW / name / "sewer.geojson", url=SEWER_URL, bbox=bbox)
    water = cached_layer(RAW / name / "water.geojson", url=WATER_URL, bbox=bbox)
    bldgs = cached_layer(RAW / name / "buildings.geojson", url=BLDG_URL, where=f"TOWN_ID={town_id}")

    gdf["use3"] = gdf["USE_CODE"].astype(str).str[:3]
    res = gdf[gdf["use3"].isin(USE_KEEP)].copy()
    res["use_type"] = res["use3"].map(USE_KEEP)
    res["poly_sqft"] = res.geometry.area * SQFT_PER_M2
    res["lot_sqft"] = res.apply(lot_sqft, axis=1)

    pts = res.geometry.representative_point()
    res["in_sewer"] = pts.within(sewer.union_all()) if len(sewer) else False
    res["in_water"] = pts.within(water.union_all()) if len(water) else False

    # Building coverage per lot (validation target for the vision model).
    inter = gpd.overlay(res[["LOC_ID", "geometry"]], bldgs[["geometry"]], how="intersection", keep_geom_type=True)
    bsqft = (inter.geometry.area * SQFT_PER_M2).groupby(inter["LOC_ID"]).sum()
    res["bldg_sqft"] = res["LOC_ID"].map(bsqft).fillna(0.0)
    res["building_pct"] = (100 * res["bldg_sqft"] / res["poly_sqft"]).clip(0, 100).round(1)

    res["meets_size"] = res["lot_sqft"] >= Q7_MIN_SQFT
    res["q7_infra_ok"] = res["in_sewer"] & res["in_water"]
    # Upper bound only; frontage cap (floor(frontage/50)) still to add.
    res["paper_lots"] = (res["lot_sqft"] // Q7_MIN_SQFT).astype(int)

    keep = ["LOC_ID", "SITE_ADDR", "use_type", "USE_CODE", "ZONING", "lot_sqft", "poly_sqft",
            "BLDG_VAL", "LAND_VAL", "YEAR_BUILT", "in_sewer", "in_water", "q7_infra_ok",
            "meets_size", "paper_lots", "bldg_sqft", "building_pct", "geometry"]
    out = res[[c for c in keep if c in res.columns]].copy()
    for c in ("lot_sqft", "poly_sqft", "bldg_sqft"):
        out[c] = out[c].round(0)
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_crs(4326).to_file(OUT / f"{name}_lots.geojson", driver="GeoJSON",
                             COORDINATE_PRECISION=6)

    qualifies = out["q7_infra_ok"] & out["meets_size"]
    return {
        "town": name, "town_id": town_id,
        "residential_lots": int(len(out)),
        "single_family": int((out["use_type"] == "single_family").sum()),
        "vacant": int((out["use_type"] != "single_family").sum()),
        "in_sewer": int(out["in_sewer"].sum()),
        "in_water": int(out["in_water"].sum()),
        "sewer_and_water": int(out["q7_infra_ok"].sum()),
        "qualify_size_and_infra": int(qualifies.sum()),
        "splittable_10k_plus": int((qualifies & (out["lot_sqft"] >= 2 * Q7_MIN_SQFT)).sum()),
        "buildings_in_town": int(len(bldgs)),
    }


def main(argv: list[str]) -> None:
    names = [a.lower() for a in argv] or list(TOWNS)
    summary_path = OUT / "towns_summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    for n in names:
        if n not in TOWNS:
            sys.exit(f"unknown town {n!r}; choose from {', '.join(TOWNS)}")
        summary[n] = build_town(n, TOWNS[n])
        print(json.dumps(summary[n]), flush=True)
        OUT.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
