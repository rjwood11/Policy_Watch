"""Refresh Census ACS indicators and ranks while preserving other county layers."""
from __future__ import annotations

import math

import geopandas as gpd
import pandas as pd
import requests

from scripts.common import prototype_config as config
from scripts.common.source_archive import archived_refresh
from scripts.download import data_fetchers as fetchers
from scripts.refresh.online_sources import TODAY, latest_census, record, transaction
from scripts.refresh.weekly_layers import read_json, write_json
from scripts.summaries.county_contracts import RANKING_BASIS, _rank_entry, _rank_values
from scripts.validate.validate_prototype_outputs import validate_outputs


def validate_acs(frame: pd.DataFrame, expected_geoids: set[str]) -> None:
    if frame.geoid.duplicated().any() or set(frame.geoid) != expected_geoids:
        raise ValueError("ACS must contain exactly one record for each Tennessee county")
    for row in frame.itertuples():
        if not math.isfinite(float(row.population)) or row.population <= 0:
            raise ValueError("ACS contains an invalid county population")
        if not math.isfinite(float(row.poverty_rate)) or not 0 <= row.poverty_rate <= 100:
            raise ValueError("ACS contains an invalid county poverty rate")


def apply_acs(frame: pd.DataFrame, year: int) -> None:
    counties = gpd.read_file(config.LAYERS_DIR / "counties.geojson")
    validate_acs(frame, set(counties.GEOID))
    if len(counties) != 95:
        raise ValueError("Expected all 95 Tennessee county boundaries")
    values = frame.set_index("geoid").to_dict(orient="index")
    ranks = {
        "population": _rank_values([(row.geoid, float(row.population)) for row in frame.itertuples()]),
        "povertyRate": _rank_values([(row.geoid, round(float(row.poverty_rate), 1)) for row in frame.itertuples()]),
    }
    for county in counties.itertuples():
        path = config.COUNTIES_DIR / f"{county.slug}.json"
        payload = read_json(path)
        value = values[county.GEOID]
        payload["population"] = int(value["population"])
        payload["buildDate"] = TODAY
        for metric in ranks:
            payload["rankings"][metric] = _rank_entry(ranks[metric][county.GEOID], len(counties), RANKING_BASIS[metric])
        for indicator in payload["indicators"]:
            if indicator["key"] == "acs-pop":
                indicator.update(value=f"{payload['population']:,}", updatedAt=TODAY,
                                 definition=f"U.S. Census Bureau ACS {year - 4}–{year} five-year county population estimate.",
                                 stateRank=payload["rankings"]["population"])
            elif indicator["key"] == "acs-poverty":
                indicator.update(value=f"{value['poverty_rate']:.1f}%", updatedAt=TODAY,
                                 definition=f"Share of people below the poverty level, calculated from U.S. Census Bureau ACS {year - 4}–{year} table B17001.",
                                 stateRank=payload["rankings"]["povertyRate"])
        write_json(path, payload)
    sources = read_json(config.METADATA_DIR / "data-sources.json")
    for source in sources:
        if source["dataset"] == "ACS indicators":
            source.update(
                sourceName=f"U.S. Census ACS {year} 5-year API",
                sourceUrl=f"https://api.census.gov/data/{year}/acs/acs5.html",
                notes=config.acs_source_notes(year),
            )
    write_json(config.METADATA_DIR / "data-sources.json", sources)
    record({"ACS indicators"}, "Current", successful=True)
    dates = read_json(config.METADATA_DIR / "last-updated.json")
    dates["county-pages"] = TODAY
    write_json(config.METADATA_DIR / "last-updated.json", dates)
    errors = validate_outputs()
    if errors:
        raise ValueError("\n".join(errors))
    report_path = config.METADATA_DIR / "refresh-run.json"
    if report_path.exists():
        report = read_json(report_path)
        report["checkedAt"] = TODAY
        report["failures"] = [failure for failure in report.get("failures", []) if not failure.startswith("ACS indicators:")]
        report.setdefault("recoveredOnRetry", []).append(f"ACS {year} indicators refreshed successfully for all 95 counties.")
        write_json(report_path, report)


@archived_refresh("Census ACS refresh")
def refresh() -> None:
    with requests.Session() as session:
        year = latest_census(session, "acs")
    previous_url = fetchers.ACS_URL
    try:
        fetchers.ACS_URL = f"https://api.census.gov/data/{year}/acs/acs5"
        frame = fetchers.load_acs()  # Fresh data required; never advance dates from fallback data.
    finally:
        fetchers.ACS_URL = previous_url
    transaction(lambda: apply_acs(frame, year))
    print(f"Refreshed ACS {year} five-year indicators and rankings for all 95 Tennessee counties.")


if __name__ == "__main__":
    refresh()
