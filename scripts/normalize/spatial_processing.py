from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import geopandas as gpd

from scripts.common.prototype_config import AREA_CRS


def simplify_for_web(frame: gpd.GeoDataFrame, tolerance_meters: float) -> gpd.GeoDataFrame:
    projected = frame.to_crs(AREA_CRS).copy()
    projected["geometry"] = projected.geometry.simplify(tolerance_meters, preserve_topology=True)
    return projected.to_crs("EPSG:4326")


def write_geojson(frame: gpd.GeoDataFrame, path: Path) -> None:
    json_data = json.loads(frame.to_json())
    path.write_text(json.dumps(json_data, separators=(",", ":")), encoding="utf8")


def spatial_labels(
    counties: gpd.GeoDataFrame,
    other: gpd.GeoDataFrame,
    *,
    county_label: str,
    other_label: str,
    display_builder: Callable,
    min_share: float = 0.0,
) -> dict[str, list[str]]:
    county_proj = counties[[county_label, "geometry"]].to_crs(AREA_CRS)
    county_proj["county_area"] = county_proj.geometry.area
    other_proj = other[[other_label, "geometry"]].to_crs(AREA_CRS)
    intersections = gpd.overlay(county_proj, other_proj, how="intersection")
    intersections["area"] = intersections.geometry.area
    intersections["share"] = intersections["area"] / intersections["county_area"]
    if min_share > 0:
        intersections = intersections[intersections["share"] >= min_share].copy()
    intersections = intersections.sort_values([county_label, "area"], ascending=[True, False])

    mapping: dict[str, list[str]] = {}
    for geoid, group in intersections.groupby(county_label):
        labels = [display_builder(row) for _, row in group.iterrows()]
        mapping[str(geoid)] = list(dict.fromkeys(labels))
    return mapping
