from __future__ import annotations

import json
import os
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from scripts.common.prototype_config import (
    ACS_URL,
    ACTIVE_PERMITS_PATH,
    COUNTIES_DIR,
    COUNTY_MAP_CITIES_PATH,
    COUNTY_MAP_MAJOR_ROADS_PATH,
    COUNTY_MAP_RIVERS_PATH,
    COUNTY_MAP_TOWNS_PATH,
    COUNTY_ZIP_URL,
    IMPAIRMENT_2026_PATH,
    JUSTICE40_PATH,
    LAYERS_DIR,
    MONITORING_STATIONS_PATH,
    RAW_DIR,
    REGION_COUNTIES_PATH,
    SCENIC_RIVERS_PATH,
    TENNESSEE_STATEFP,
    TN_LEG_URL,
    WBD_HUC8_URL,
    WATER_SERVICE_AREAS_PATH,
)


def fetch_json(url: str, *, params: dict[str, str] | None = None) -> dict:
    response = requests.get(url, params=params, timeout=120)
    response.raise_for_status()
    return response.json()


def fetch_geojson(url: str, *, params: dict[str, str]) -> gpd.GeoDataFrame:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=120)
            response.raise_for_status()
            payload = response.json()
            return gpd.GeoDataFrame.from_features(payload["features"], crs="EPSG:4326")
        except (KeyError, ValueError, requests.RequestException) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))

    raise RuntimeError(f"GeoJSON request failed for {url}: {last_error}") from last_error


def _load_cached_public_layer(filename: str) -> gpd.GeoDataFrame:
    path = LAYERS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing cached public layer: {path}")
    return gpd.read_file(path)


def load_tennessee_counties() -> gpd.GeoDataFrame:
    local_zip = RAW_DIR / "tl_2024_us_county.zip"
    if not local_zip.exists():
        response = requests.get(COUNTY_ZIP_URL, timeout=180)
        response.raise_for_status()
        local_zip.write_bytes(response.content)

    with zipfile.ZipFile(local_zip) as archive:
        shapefile_name = next(name for name in archive.namelist() if name.endswith(".shp"))
        shapefile_path = f"/vsizip/{local_zip.resolve()}/{Path(shapefile_name).name}"

    counties = gpd.read_file(shapefile_path)
    counties = counties[counties["STATEFP"] == TENNESSEE_STATEFP].copy()
    counties["slug"] = counties["NAME"].str.lower().str.replace(" ", "-", regex=False)
    counties = counties[["GEOID", "NAME", "NAMELSAD", "slug", "geometry"]].sort_values("NAME")
    return counties


def load_huc8() -> gpd.GeoDataFrame:
    try:
        huc8 = fetch_geojson(
            WBD_HUC8_URL,
            params={
                "where": "states LIKE '%TN%'",
                "outFields": "huc8,name,states,areasqkm",
                "returnGeometry": "true",
                "f": "geojson",
            },
        )
    except RuntimeError:
        huc8 = _load_cached_public_layer("huc8.geojson")
    return huc8[["huc8", "name", "states", "areasqkm", "geometry"]].sort_values("huc8")


def load_legislative_layer(layer_id: int) -> gpd.GeoDataFrame:
    try:
        layer = fetch_geojson(
            f"{TN_LEG_URL}/{layer_id}/query",
            params={
                "where": "1=1",
                "outFields": "DISTRICT,NAME,POPULATION",
                "returnGeometry": "true",
                "f": "geojson",
            },
        )
    except RuntimeError:
        cached_layers = {
            0: "senate-districts.geojson",
            1: "house-districts.geojson",
            2: "congressional-districts.geojson",
        }
        layer = _load_cached_public_layer(cached_layers[layer_id])
    layer["DISTRICT"] = layer["DISTRICT"].astype(str)
    return layer[["DISTRICT", "NAME", "POPULATION", "geometry"]].sort_values("DISTRICT")


def _load_cached_acs(counties: gpd.GeoDataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for county in counties.itertuples():
        county_path = COUNTIES_DIR / f"{county.slug}.json"
        if not county_path.exists():
            raise FileNotFoundError(f"Missing cached county payload for ACS fallback: {county_path}")

        payload = json.loads(county_path.read_text(encoding="utf8"))
        indicators = {indicator["key"]: indicator for indicator in payload.get("indicators", [])}
        poverty_value = str(indicators.get("acs-poverty", {}).get("value", "0")).replace("%", "")
        rows.append(
            {
                "geoid": county.GEOID,
                "NAME": f"{county.NAME} County, Tennessee",
                "population": int(payload.get("population", 0)),
                "median_income": pd.NA,
                "poverty_rate": float(poverty_value),
            }
        )

    return pd.DataFrame(rows)


def load_acs(counties: gpd.GeoDataFrame | None = None) -> pd.DataFrame:
    params = {
        "get": "NAME,B01003_001E,B19013_001E,B17001_001E,B17001_002E",
        "for": "county:*",
        "in": "state:47",
    }
    api_key = os.getenv("CENSUS_API_KEY")
    if api_key:
        params["key"] = api_key

    response = requests.get(ACS_URL, params=params, timeout=120)
    response.raise_for_status()
    try:
        rows = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        if counties is not None:
            return _load_cached_acs(counties)
        raise RuntimeError(
            f"ACS request returned non-JSON from {response.url}. Set CENSUS_API_KEY or pass counties for cached fallback."
        ) from exc

    frame = pd.DataFrame(rows[1:], columns=rows[0])
    frame["geoid"] = frame["state"] + frame["county"]
    frame["population"] = frame["B01003_001E"].astype(int)
    frame["median_income"] = frame["B19013_001E"].replace("-666666666", pd.NA).astype("Int64")
    frame["poverty_total"] = frame["B17001_001E"].astype(int)
    frame["poverty_count"] = frame["B17001_002E"].astype(int)
    frame["poverty_rate"] = (frame["poverty_count"] / frame["poverty_total"]) * 100
    return frame[["geoid", "NAME", "population", "median_income", "poverty_rate"]]


def load_region_counties() -> gpd.GeoDataFrame:
    return gpd.read_file(REGION_COUNTIES_PATH)[["GEOID", "NAME", "Region", "geometry"]]


def load_justice40() -> gpd.GeoDataFrame:
    return gpd.read_file(JUSTICE40_PATH)


def load_impairment_2026() -> gpd.GeoDataFrame:
    return gpd.read_file(IMPAIRMENT_2026_PATH)


def load_monitoring_stations() -> gpd.GeoDataFrame:
    return gpd.read_file(MONITORING_STATIONS_PATH)


def load_scenic_rivers() -> gpd.GeoDataFrame:
    return gpd.read_file(SCENIC_RIVERS_PATH)


def load_active_permits() -> gpd.GeoDataFrame:
    return gpd.read_file(ACTIVE_PERMITS_PATH)


def load_water_service_areas() -> gpd.GeoDataFrame:
    return gpd.read_file(WATER_SERVICE_AREAS_PATH)


def load_county_map_rivers() -> gpd.GeoDataFrame:
    return gpd.read_file(COUNTY_MAP_RIVERS_PATH)


def load_county_map_cities() -> gpd.GeoDataFrame:
    return gpd.read_file(COUNTY_MAP_CITIES_PATH)


def load_county_map_towns() -> gpd.GeoDataFrame:
    return gpd.read_file(COUNTY_MAP_TOWNS_PATH)


def load_county_map_major_roads() -> gpd.GeoDataFrame:
    return gpd.read_file(COUNTY_MAP_MAJOR_ROADS_PATH)
