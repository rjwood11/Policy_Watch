"""Refresh district maps and county overlap lists without rebuilding unrelated data."""
from __future__ import annotations

import json

import geopandas as gpd
import requests

from scripts.common import prototype_config as config
from scripts.common.source_archive import archived_refresh
from scripts.common.file_io import write_text_atomic
from scripts.download.data_fetchers import download_congressional_districts
from scripts.normalize.spatial_processing import simplify_for_web, spatial_labels, write_geojson
from scripts.refresh.online_sources import TODAY, geo, record, registry, transaction
from scripts.refresh.weekly_layers import read_json, write_json
from scripts.summaries.county_contracts import _clip_to_county_viewport, _feature_collection
from scripts.validate.validate_prototype_outputs import validate_outputs


@archived_refresh("Legislative district refresh")
def refresh() -> None:
    with requests.Session() as session:
        layers = {key: geo(session, f"{config.TN_LEG_URL}/{number}")
                  for key, number in [("senate", 0), ("house", 1)]}
        layers["congressional"] = download_congressional_districts(session)
    for key, count in [("senate", 33), ("house", 99), ("congressional", 9)]:
        frame = layers[key]
        frame["DISTRICT"] = frame.DISTRICT.astype(int).astype(str)
        if len(frame) != count or set(frame.DISTRICT) != {str(i) for i in range(1, count + 1)}:
            raise ValueError(f"Missing or duplicate {key} districts")

    counties = gpd.read_file(config.LAYERS_DIR / "counties.geojson")
    labels = {}
    for key, frame in layers.items():
        labels[key] = spatial_labels(
            counties, frame, county_label="GEOID", other_label="DISTRICT", min_share=0.005,
            display_builder=lambda row, key=key: (
                f"TN-{int(row['DISTRICT']):02d}" if key == "congressional"
                else f"{key.title()} {row['DISTRICT']}"
            ),
        )

    def apply():
        for key, frame in layers.items():
            write_geojson(simplify_for_web(frame, 250), config.LAYERS_DIR / f"{key}-districts.geojson")
        for county in counties.itertuples():
            county_frame = counties[counties.GEOID == county.GEOID].copy()
            path = config.COUNTY_MAPS_DIR / f"{county.slug}.json"
            payload = read_json(path)
            for key, frame in layers.items():
                clipped = _clip_to_county_viewport(
                    frame.rename(columns={"DISTRICT": "district"}), county_frame,
                    simplify_meters=140, keep_columns=["district"],
                )
                payload["districts"][key] = _feature_collection(clipped)
            write_text_atomic(path, json.dumps(payload, separators=(",", ":")))
            path = config.COUNTIES_DIR / f"{county.slug}.json"
            payload = read_json(path)
            payload["legislativeDistricts"] = labels["senate"].get(county.GEOID, []) + labels["house"].get(county.GEOID, [])
            payload["congressionalDistricts"] = labels["congressional"].get(county.GEOID, [])
            payload["buildDate"] = TODAY
            write_json(path, payload)
        sources = registry()
        for source in sources:
            if source["dataset"] == "Legislative districts":
                source.update(sourceName="TNMap state districts / Comptroller congressional plan",
                              sourceUrl="https://comptroller.tn.gov/maps.html", notes=config.DISTRICT_SOURCE_NOTES)
        write_json(config.METADATA_DIR / "data-sources.json", sources)
        record({"Legislative districts"}, "Current", successful=True)
        errors = validate_outputs()
        if errors:
            raise ValueError("\n".join(errors))
    transaction(apply)
    print("Updated all 33 Senate, 99 House, and 9 congressional districts across 95 county maps.")


if __name__ == "__main__":
    refresh()
