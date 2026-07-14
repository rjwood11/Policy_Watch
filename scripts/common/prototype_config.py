from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DATA = ROOT / "public" / "data"
LAYERS_DIR = PUBLIC_DATA / "layers"
COUNTIES_DIR = PUBLIC_DATA / "counties"
METADATA_DIR = PUBLIC_DATA / "metadata"
SEARCH_DIR = PUBLIC_DATA / "search"
COUNTY_MAPS_DIR = PUBLIC_DATA / "county-maps"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"
EXTERNAL_DIR = ROOT / "data" / "external" / "harpeth_conservancy"

TENNESSEE_STATEFP = "47"
AREA_CRS = "EPSG:5070"

COUNTY_ZIP_URL = "https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip"
ACS_URL = "https://api.census.gov/data/2024/acs/acs5"
WBD_HUC8_URL = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query"
TN_LEG_URL = "https://tnmap.tn.gov/arcgis/rest/services/ADMINISTRATIVE_BOUNDARIES/LEGISLATIVE_DISTRICTS/MapServer"
CEJST_QUERY_URL = "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/usa_november_2022/FeatureServer/0/query"
ATTAINS_ASSESSMENTS_URL = "https://attains.epa.gov/attains-public/api/assessments"
ATTAINS_ASSESSMENT_UNITS_URL = "https://attains.epa.gov/attains-public/api/assessmentUnits"

ATTAINS_CATEGORIES = ["1", "2", "3", "4A", "4B", "4C", "4D", "5"]
ATTAINS_CATEGORY_LABELS = {
    "1": "Category 1: all uses attained",
    "2": "Category 2: some uses attained, others not assessed",
    "3": "Category 3: insufficient information",
    "4A": "Category 4A: TMDL completed",
    "4B": "Category 4B: other required controls",
    "4C": "Category 4C: impairment not caused by a pollutant",
    "4D": "Category 4D: impaired, but not needing a TMDL",
    "5": "Category 5: impaired, TMDL needed",
    "unassigned": "No current category in the reporting feed",
}

FEATURED_COUNTIES = {
    "47037": {
        "slug": "davidson",
        "region": "Middle Tennessee",
        "focus": "urban river corridors, growth pressure, and environmental justice context",
    },
    "47187": {
        "slug": "williamson",
        "region": "Middle Tennessee",
        "focus": "Harpeth River health, suburban growth, and local land-use decisions",
    },
    "47021": {
        "slug": "cheatham",
        "region": "Middle Tennessee",
        "focus": "downstream watershed context, local infrastructure choices, and river health communication",
    },
    "47157": {
        "slug": "shelby",
        "region": "West Tennessee",
        "focus": "urban environmental health communication, screening-tool caveats, and river-adjacent policy context",
    },
}

REGION_COUNTIES_PATH = EXTERNAL_DIR / "tn_counties_region" / "All Counties by Region.shp"
JUSTICE40_PATH = EXTERNAL_DIR / "justice40" / "ATP and Justice40.shp"
IMPAIRMENT_2026_PATH = EXTERNAL_DIR / "impairment_2026" / "303d list 2026.shp"
MONITORING_STATIONS_PATH = EXTERNAL_DIR / "monitoring_stations" / "Water_Quality_Monitoring_Stations.shp"
SCENIC_RIVERS_PATH = EXTERNAL_DIR / "scenic_rivers" / "Scenic_Rivers_line.shp"
ACTIVE_PERMITS_PATH = EXTERNAL_DIR / "active_water_permits" / "Active_Permitted_Features.shp"
WATER_SERVICE_AREAS_PATH = EXTERNAL_DIR / "water_service_areas" / "TN_Public_Water_System_Service_Area_Boundaries.shp"
COUNTY_MAP_RIVERS_PATH = EXTERNAL_DIR / "county_map_sources" / "rivers" / "RiversFINAL.shp"
COUNTY_MAP_CITIES_PATH = EXTERNAL_DIR / "county_map_sources" / "cities" / "Tennessee Cities.shp"
COUNTY_MAP_TOWNS_PATH = EXTERNAL_DIR / "county_map_sources" / "towns" / "Tennessee Towns.shp"
COUNTY_MAP_MAJOR_ROADS_PATH = EXTERNAL_DIR / "county_map_sources" / "major_roads.geojson"


@dataclass(frozen=True)
class BuildContext:
    build_date: str


def get_build_context() -> BuildContext:
    build_date = os.getenv("POLICYWATCH_DATA_DATE", date.today().isoformat())
    return BuildContext(build_date=build_date)


def ensure_dirs() -> None:
    for directory in [LAYERS_DIR, COUNTIES_DIR, METADATA_DIR, SEARCH_DIR, COUNTY_MAPS_DIR, PROCESSED_DIR, RAW_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
