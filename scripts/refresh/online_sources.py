"""Refresh online inputs and rebuild maps without redating local GIS snapshots.

The GIS build is transactional: download and validate online inputs first,
then rebuild together, retaining unavailable overlays and ACS. A build failure
restores the previous public files. Weekly
permit/compliance caches, Superfund, and NLCD run independently.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import geopandas as gpd

from scripts.common import prototype_config as config
from scripts.download import data_fetchers as fetchers
from scripts.refresh.weekly_layers import fetch_paged_geojson, read_json, write_json, request_json
from scripts.summaries.build_prototype_data import main as build_data
import requests

GIS_DATASETS = {
    "Tennessee counties": "counties",
    "HUC6 basins": "huc6-basins",
    "HUC8 watersheds": "watersheds",
    "Legislative districts": "districts",
    "ACS indicators": "acs",
    "Public water system service areas": "water-service-areas",
    "Lead service line inventory": "service-line-inventory",
    "Solid waste landfill permit locations": "tdec-solid-waste-landfills",
    "Protected areas and conservation easements": "protected-areas",
}
LIVE_DATASETS = {"EPA ATTAINS assessment geospatial layer", "TNMap composite address locator"}
TODAY = date.today().isoformat()


def registry() -> list[dict]:
    return read_json(config.METADATA_DIR / "data-sources.json")


def record(names, status: str, *, successful: bool = False) -> None:
    sources = registry()
    dates = read_json(config.METADATA_DIR / "last-updated.json")
    for source in sources:
        if source["dataset"] in names:
            source.update(lastChecked=TODAY, refreshStatus=status)
            if successful:
                source["lastUpdated"] = TODAY
                dates[GIS_DATASETS.get(source["dataset"], {
                    "Superfund sites": "superfund", "Land use / land cover": "land-cover"
                }.get(source["dataset"], source["dataset"]))] = TODAY
    write_json(config.METADATA_DIR / "data-sources.json", sources)
    write_json(config.METADATA_DIR / "last-updated.json", dates)


def transaction(action) -> None:
    # Back up only generated public data; never move or remove the workspace.
    with tempfile.TemporaryDirectory(prefix="policywatch-refresh-") as directory:
        backup = Path(directory) / "data"
        shutil.copytree(config.PUBLIC_DATA, backup)
        try:
            action()
        except (Exception, SystemExit) as exc:
            for path in backup.rglob("*"):
                if path.is_file():
                    target = config.PUBLIC_DATA / path.relative_to(backup)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
            # Remove newly generated files that had no previous counterpart.
            for path in config.PUBLIC_DATA.rglob("*"):
                if path.is_file() and not (backup / path.relative_to(config.PUBLIC_DATA)).exists():
                    path.unlink()
            if isinstance(exc, SystemExit):
                raise RuntimeError(f"Data build validation failed: {exc}") from exc
            raise


def geo(session, url, where="1=1", fields="*"):
    print(f"Downloading {url}...", flush=True)
    metadata = request_json(session, url.removesuffix('/query'), params={"f": "json"})
    oid = metadata.get("objectIdField") or next(
        field["name"] for field in metadata.get("fields", []) if field["type"] == "esriFieldTypeOID"
    )
    payload = fetch_paged_geojson(session, f"{url.removesuffix('/query')}/query", {
        "where": where, "outFields": fields, "returnGeometry": "true",
        "outSR": "4326", "f": "geojson", "orderByFields": oid,
    }, max_pages=500)
    if not payload["features"]:
        raise ValueError(f"Unexpected empty GIS dataset: {url}")
    return gpd.GeoDataFrame.from_features(payload["features"], crs="EPSG:4326")


def latest_census(session, kind: str):
    # Probe release metadata, treating only 404 as an unpublished year.
    for year in range(date.today().year, 2023, -1):
        url = (f"https://api.census.gov/data/{year}/acs/acs5/variables.json" if kind == "acs"
               else f"https://www2.census.gov/geo/tiger/TIGER{year}/COUNTY/")
        response = session.get(url, timeout=120)
        if response.status_code == 404:
            continue
        response.raise_for_status()
        if kind == "acs":
            if "B01003_001E" not in response.json().get("variables", {}):
                raise ValueError("Census returned unexpected ACS metadata")
        elif f"tl_{year}_us_county.zip" not in response.text:
            continue
        return year
    raise ValueError(f"No supported published Census {kind} release found")


def refresh_gis() -> list[str]:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 PolicyWatch/0.1",
                            "Origin": "https://tdeconline.tn.gov", "Referer": "https://tdeconline.tn.gov/"})
    county_year = latest_census(session, "counties")
    acs_year = latest_census(session, "acs")
    county_url = f"https://www2.census.gov/geo/tiger/TIGER{county_year}/COUNTY/tl_{county_year}_us_county.zip"
    response = session.get(county_url, timeout=180)
    response.raise_for_status()
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    archive = config.RAW_DIR / f"tl_{county_year}_us_county.zip"
    archive.write_bytes(response.content)
    counties = gpd.read_file(archive)
    counties = counties[counties.STATEFP == "47"].copy()
    counties["slug"] = counties.NAME.str.lower().str.replace(" ", "-", regex=False)
    counties = counties[["GEOID", "NAME", "NAMELSAD", "slug", "geometry"]].sort_values("NAME")
    if len(counties) != 95:
        raise ValueError("Census did not return all 95 Tennessee counties")
    acs_url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
    old_acs_url = fetchers.ACS_URL
    unavailable = {}
    overlay_names = {"acs": "ACS indicators", "water_service_areas": "Public water system service areas",
                     "service_line_inventory": "Lead service line inventory",
                     "solid_waste_landfills": "Solid waste landfill permit locations",
                     "protected_areas": "Protected areas and conservation easements"}
    try:
        fetchers.ACS_URL = acs_url
        acs = fetchers.load_acs()  # No cached fallback: successful dates must mean fresh data.
    except Exception as exc:
        unavailable["acs"] = str(exc)
        print(f"::warning::ACS indicators: {exc}; retaining previous indicators", flush=True)
        acs = fetchers._load_cached_acs(counties)
    finally:
        fetchers.ACS_URL = old_acs_url
    if set(acs.geoid) != set(counties.GEOID):
        raise ValueError("ACS response is missing Tennessee counties")
    inputs = {"counties": counties, "acs": acs}
    for key, url in [("huc6", config.WBD_HUC6_URL), ("huc8", config.WBD_HUC8_URL)]:
        inputs[key] = geo(session, url, "states LIKE '%TN%'")
    for key, layer in [("senate", 0), ("house", 1), ("congress", 2)]:
        frame = geo(session, f"{config.TN_LEG_URL}/{layer}")
        frame["DISTRICT"] = frame.DISTRICT.astype(str)
        inputs[key] = frame
    for key, url, where in [
        ("water_service_areas", config.TDEC_WATER_SERVICE_AREAS_URL, "1=1"),
        ("service_line_inventory", config.TDEC_SERVICE_LINE_INVENTORY_URL, "1=1"),
        ("solid_waste_landfills", config.TDEC_SOLID_WASTE_PERMITS_URL,
         "PERMIT_TYPE IN ('CLASS I','CLASS II','CLASS III','CLASS IV','COAL ASH')"),
        ("protected_areas", config.PADUS_PROTECTION_MECHANISM_URL, "State_Nm = 'TN'"),
    ]:
        try:
            inputs[key] = geo(session, url, where)
        except Exception as exc:
            unavailable[key] = str(exc)
            print(f"::warning::{overlay_names[key]}: {exc}; retaining previous layer", flush=True)
            if key == "water_service_areas":
                inputs[key] = fetchers.load_water_service_areas()
            else:
                fields = {"service_line_inventory": fetchers.TDEC_SERVICE_LINE_INVENTORY_FIELDS,
                          "solid_waste_landfills": fetchers.TDEC_LANDFILL_FIELDS,
                          "protected_areas": fetchers.PADUS_PROTECTED_AREAS_FIELDS}[key]
                inputs[key] = gpd.GeoDataFrame(columns=[*fields, "geometry"], crs="EPSG:4326")
    if "water_service_areas" in unavailable:
        unavailable["service_line_inventory"] = "Service-area boundaries unavailable; related utility layer retained"
    previous_maps = {path.stem: read_json(path) for path in config.COUNTY_MAPS_DIR.glob("*.json")}
    previous_sources = registry()
    previous_dates = read_json(config.METADATA_DIR / "last-updated.json")
    indicator_dates = {}
    for path in config.COUNTIES_DIR.glob("*.json"):
        if path.stem != "index":
            payload = read_json(path)
            indicator_dates[path.stem] = payload

    def rebuild():
        build_data(inputs)
        # The general builder dates every input; restore provenance for snapshots
        # and independently refreshed layers before advancing successful sources.
        write_json(config.METADATA_DIR / "data-sources.json", previous_sources)
        write_json(config.METADATA_DIR / "last-updated.json", previous_dates)
        for slug, previous in indicator_dates.items():
            path = config.COUNTIES_DIR / f"{slug}.json"
            payload = read_json(path)
            old = {item["key"]: item for item in previous["indicators"]}
            for item in payload["indicators"]:
                if item["sourceDataset"] != "ACS indicators" or "acs" in unavailable:
                    item["updatedAt"] = old[item["key"]]["updatedAt"]
            payload["stressSummary"]["updatedAt"] = previous["stressSummary"]["updatedAt"]
            if "water_service_areas" in unavailable:
                payload["waterServiceSummary"] = previous["waterServiceSummary"]
                payload["rankings"]["waterServiceAreas"] = previous["rankings"]["waterServiceAreas"]
            write_json(path, payload)
            map_path = config.COUNTY_MAPS_DIR / f"{slug}.json"
            county_map = read_json(map_path)
            old_map = previous_maps[slug]
            for key, field in [("solid_waste_landfills", "landfills"), ("protected_areas", "protectedAreas"),
                               ("water_service_areas", "waterUtilities")]:
                if key in unavailable:
                    county_map[field] = old_map[field]
            if "service_line_inventory" in unavailable and "water_service_areas" not in unavailable:
                fields = ["total_lines", "lead_lines", "non_lead_lines", "grr_lines", "unknown_lines", "service_line_inventory_status"]
                old_utilities = {f["properties"]["pwsid"]: f["properties"] for f in old_map["waterUtilities"]["features"]}
                for feature in county_map["waterUtilities"]["features"]:
                    properties = feature["properties"]
                    old = old_utilities.get(properties["pwsid"])
                    if old:
                        properties.update({field: old.get(field) for field in fields})
            map_path.write_text(json.dumps(county_map, separators=(",", ":")), encoding="utf8")
        sources = registry()
        for source in sources:
            if source["dataset"] == "ACS indicators" and "acs" not in unavailable:
                source.update(sourceName=f"U.S. Census ACS {acs_year} 5-year API", sourceUrl=f"{acs_url}.html")
            if source["dataset"] == "Tennessee counties":
                source.update(sourceName=f"Census TIGER/Line {county_year} Counties", sourceUrl=county_url)
            if source["dataset"] == "Public water system service areas":
                source["notes"] = "Refreshed from TDEC's online service. County summaries and map polygons are rebuilt together; service-line inventory values are joined by PWSID."
        write_json(config.METADATA_DIR / "data-sources.json", sources)
        retained = {overlay_names[key] for key in unavailable}
        record(set(GIS_DATASETS) - retained, "Current", successful=True)
        record(retained, "Refresh failed; previous data retained")
        dates = read_json(config.METADATA_DIR / "last-updated.json")
        dates["county-pages"] = TODAY
        write_json(config.METADATA_DIR / "last-updated.json", dates)
    transaction(rebuild)
    return [f"{overlay_names[key]}: {message}" for key, message in unavailable.items()]


def refresh_landcover() -> None:
    from scripts.refresh import landuse
    response = requests.get(landuse.SOURCE_URL, params={
        "service": "WCS", "version": "2.0.1", "request": "DescribeCoverage", "coverageId": landuse.COVERAGE.replace(":", "__"),
    }, timeout=120)
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    years = [int(match.group(1)) for element in root.iter()
             if element.tag.split("}")[-1] == "timePosition"
             for match in [re.match(r"(20\d{2})-", element.text or "")] if match]
    if not years:
        raise ValueError("USGS did not advertise land-cover observation years")
    year = max(years)
    if year < read_json(landuse.OUTPUT_DIR / "manifest.json")["year"]:
        raise ValueError("USGS advertised an older release; existing imagery retained")
    landuse.YEAR = year
    landuse.CACHE_PATH = config.RAW_DIR / f"annual-nlcd-{year}-tn-{landuse.RESOLUTION}m.tif"
    landuse.build_county_rasters(force=True)
    record({"Land use / land cover"}, "Current", successful=True)


def configure_registry() -> None:
    sources = registry()
    for source in sources:
        name = source["dataset"]
        if name in GIS_DATASETS or name in {"TDEC DWR public water resources permits", "EPA ECHO CWA permit compliance", "Superfund sites"}:
            source["refreshFrequency"] = "Weekly check; latest available agency release"
            source.setdefault("refreshStatus", "Awaiting first scheduled refresh")
        elif name == "Land use / land cover":
            source["refreshFrequency"] = "Monthly check for latest annual release"
            source.setdefault("refreshStatus", "Awaiting first scheduled refresh")
        elif name in LIVE_DATASETS:
            source["refreshFrequency"] = "Live queries; weekly availability check"
            source.setdefault("refreshStatus", "Live service; agency publication date varies")
        else:
            source["refreshFrequency"] = "Local snapshot; manual replacement required"
            source["refreshStatus"] = "Local snapshot"
    write_json(config.METADATA_DIR / "data-sources.json", sources)
    dates = read_json(config.METADATA_DIR / "last-updated.json")
    for source in sources:
        if source["dataset"] in {"Superfund sites", "Land use / land cover"}:
            dates["superfund" if source["dataset"] == "Superfund sites" else "land-cover"] = source["lastUpdated"]
    write_json(config.METADATA_DIR / "last-updated.json", dates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configure-only", action="store_true", help="Describe refresh policies without downloading or redating sources.")
    parser.add_argument("--include-landcover", action="store_true", help="Check imagery now rather than waiting until the first Saturday of the month.")
    args = parser.parse_args()
    configure_registry()
    if args.configure_only:
        return
    failures = []
    def run(label, names, action):
        print(f"Refreshing {label}...", flush=True)
        try:
            errors = action()
            if errors:
                failures.extend(errors)
        except Exception as exc:
            failures.append(f"{label}: {exc}")
            record(names, "Refresh failed; previous data retained")
            print(f"::warning::{label}: {exc}", flush=True)
    run("county GIS inputs", GIS_DATASETS, refresh_gis)
    from scripts.refresh.superfund import refresh_cache, apply_cached_superfund
    def superfund():
        refresh_cache()
        apply_cached_superfund()
        record({"Superfund sites"}, "Current", successful=True)
    run("Superfund", {"Superfund sites"}, lambda: transaction(superfund))
    if args.include_landcover or date.today().day <= 7:
        run("land cover", {"Land use / land cover"}, lambda: transaction(refresh_landcover))
    for source in registry():
        if source["dataset"] in LIVE_DATASETS:
            def check_live(source=source):
                response = requests.get(source["sourceUrl"], params={"f": "json"}, timeout=60)
                response.raise_for_status()
                if "error" in response.json():
                    raise ValueError("Service returned an error")
                record({source["dataset"]}, "Live service available; queried when used")
            run(source["dataset"], {source["dataset"]}, check_live)
    # Separate process keeps the weekly script's CLI and per-county failure isolation.
    result = subprocess.run([sys.executable, "-u", "-m", "scripts.refresh.weekly_layers", "--strict"], check=False)
    if result.returncode:
        failures.append("Some TDEC / ECHO counties could not refresh; see weekly manifest")
    configure_registry()
    summary = "\n".join(["## Data refresh", f"Checked: {TODAY}", *[f"- {item}" for item in failures]])
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf8") as output:
            output.write(summary + "\n")
    print(summary)
    # The workflow publishes successful sources and then reports degraded runs.
    write_json(config.METADATA_DIR / "refresh-run.json", {"checkedAt": TODAY, "failures": failures})


if __name__ == "__main__":
    main()
