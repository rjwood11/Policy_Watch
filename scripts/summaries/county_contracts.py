from __future__ import annotations

import json

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from scripts.common.prototype_config import (
    ACS_URL,
    ACTIVE_PERMITS_PATH,
    AREA_CRS,
    COUNTIES_DIR,
    COUNTY_ZIP_URL,
    COUNTY_MAPS_DIR,
    FEATURED_COUNTIES,
    IMPAIRMENT_2026_PATH,
    JUSTICE40_PATH,
    METADATA_DIR,
    MONITORING_STATIONS_PATH,
    SCENIC_RIVERS_PATH,
    SEARCH_DIR,
    TN_LEG_URL,
    WATER_SERVICE_AREAS_PATH,
)

POLYGON_VIEWPORT_FIT_PADDING_RATIO = 0.08
POLYGON_VIEWPORT_ASPECT_RATIOS = (0.5, 1.5)
POLYGON_VIEWPORT_PIXEL_PADDING_FACTOR = 1.3
POLYGON_VIEWPORT_MIN_PADDING_DEGREES = 0.02

ATTAINMENT_LABELS = {
    "Fully Supporting": "Fully supporting",
    "Fully Supporting (Evaluated)": "Fully supporting (evaluated)",
    "Not Assessed": "Not assessed",
    "Not Supporting": "Not supporting",
    "Not Supporting (Evaluated)": "Not supporting (evaluated)",
    "Threatened": "Threatened",
}

IMPAIRMENT_CAUSE_PATTERNS = [
    (
        "pathogens",
        "Pathogens / bacteria",
        ["e. coli", "e coli", "ecoli", "pathogen", "bacteria", "fecal coliform"],
    ),
    (
        "nutrients",
        "Nutrients",
        [
            "nutrients elevated",
            "nutrients consistently elevated",
            "nutrients occasionally elevated",
            "%nutol elevated",
            "%nutol much higher",
            "%nutol very high",
            "high algae",
            "algae growth",
            "algal growth",
        ],
    ),
    (
        "habitat_alterations",
        "Habitat alteration",
        ["habitat", "riparian losses", "channel alteration", "channel alterations", "channelized"],
    ),
    (
        "sediment",
        "Sediment / siltation",
        ["sediment", "sedimentation", "siltation", "erosion"],
    ),
    (
        "flow_alterations",
        "Flow / hydrologic alteration",
        ["impoundment", "flow alteration", "flow alterations", "hydrologic alteration"],
    ),
    (
        "oxygen_depletion",
        "Oxygen depletion",
        ["low d.o.", "low do", "dissolved oxygen", "oxygen depletion"],
    ),
    (
        "impaired_biota",
        "Impaired biological community",
        ["biocriteria", "sqsh", "biorecon", "stressed community", "fish & aquatic life"],
    ),
    ("mercury", "Mercury", ["mercury", " hg "]),
    (
        "metals_other_than_mercury",
        "Metals other than mercury",
        [" iron ", " lead ", " copper ", " zinc ", "metals"],
    ),
    ("temperature", "Temperature", ["temperature"]),
    ("ph", "pH", [" ph ", "ph impairment", "ph criteria"]),
]

ROAD_STYLES = {
    "motorway": "motorway",
    "motorway_link": "motorway",
    "trunk": "trunk",
    "trunk_link": "trunk",
    "primary": "primary",
    "primary_link": "primary",
}

RANKING_BASIS = {
    "population": "Ranked by ACS county population, high to low.",
    "povertyRate": "Ranked by ACS county poverty rate, high to low.",
    "disadvantagedTractShare": "Ranked by share of county tracts flagged as disadvantaged, high to low.",
    "impairedRiverMiles": "Ranked by impaired river miles, high to low.",
    "fullAttainmentRiverMiles": "Ranked by full-attainment river miles, high to low.",
    "notAssessedRiverMiles": "Ranked by not-assessed river miles, high to low.",
    "otherAssessedRiverMiles": "Ranked by other assessed river miles, high to low.",
    "monitoringStations": "Ranked by distinct monitoring stations, high to low.",
    "activePermits": "Ranked by active permitted water features, high to low.",
    "scenicRiverMiles": "Ranked by designated scenic river miles, high to low.",
    "waterServiceAreas": "Ranked by overlapping public water service areas, high to low.",
    "waterStressTractShare": "Ranked by share of county tracts carrying the CEJST water and wastewater flag, high to low.",
    "climateStressTractShare": "Ranked by share of county tracts carrying the CEJST climate flag, high to low.",
}


def _percentage(part: int | float, total: int | float) -> float:
    return round((float(part) / float(total) * 100), 1) if total else 0.0


def _ordinal(value: int) -> str:
    suffix = "th"
    if value % 100 not in {11, 12, 13}:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _rank_values(values: list[tuple[str, float]]) -> dict[str, dict[str, int]]:
    sorted_values = sorted(values, key=lambda item: (-item[1], item[0]))
    value_counts: dict[float, int] = {}
    for _, value in values:
        value_counts[value] = value_counts.get(value, 0) + 1

    ranks: dict[str, dict[str, int]] = {}
    previous_value: float | None = None
    current_rank = 0

    for position, (geoid, value) in enumerate(sorted_values, start=1):
        if previous_value is None or value != previous_value:
            current_rank = position
            previous_value = value
        ranks[geoid] = {
            "rank": current_rank,
            "tieCount": value_counts[value],
        }

    return ranks


def _rank_entry(rank_info: dict[str, int], total: int, basis: str) -> dict[str, object]:
    rank = rank_info["rank"]
    tie_count = rank_info["tieCount"]
    display_prefix = "tied " if tie_count > 1 else ""

    return {
        "rank": rank,
        "total": total,
        "tieCount": tie_count,
        "display": f"{display_prefix}{_ordinal(rank)} of {total} Tennessee counties",
        "basis": basis,
    }


def _tract_word(count: int) -> str:
    return "tract" if count == 1 else "tracts"


def _infer_impairment_causes(value: object) -> list[dict[str, str]]:
    text = f" {str(value or '').lower().replace(chr(10), ' ')} "
    text = " ".join(text.split())
    if not text:
        return []

    causes: list[dict[str, str]] = []
    for key, label, patterns in IMPAIRMENT_CAUSE_PATTERNS:
        if any(pattern in text for pattern in patterns):
            causes.append({"cause": key, "label": label})

    return causes


def summarize_justice40_by_county(justice40: gpd.GeoDataFrame) -> dict[str, dict[str, float]]:
    frame = justice40.copy()
    frame["county_geoid"] = frame["GEOID10"].astype(str).str.slice(0, 5)
    frame["identified_as_disadvantaged"] = frame["SN_C"].fillna(0).astype(int)
    frame["water_flags"] = frame["N_WTR"].fillna(0).astype(int)
    frame["climate_flags"] = frame["N_CLT"].fillna(0).astype(int)

    grouped = (
        frame.groupby("county_geoid")
        .agg(
            tract_count=("GEOID10", "count"),
            disadvantaged_tracts=("identified_as_disadvantaged", "sum"),
            water_flags=("water_flags", "sum"),
            climate_flags=("climate_flags", "sum"),
        )
        .reset_index()
    )
    return grouped.set_index("county_geoid").to_dict(orient="index")


def summarize_impairment_by_county(
    counties: gpd.GeoDataFrame,
    impairment: gpd.GeoDataFrame,
) -> dict[str, dict[str, object]]:
    county_proj = counties[["GEOID", "NAME", "geometry"]].to_crs(AREA_CRS)
    lines = impairment[impairment["WATER_TYPE"] == "RIVER"].copy().to_crs(AREA_CRS)
    intersections = gpd.overlay(
        county_proj,
        lines[["ATTAINMENT", "ASSESSME_1", "ASSESSMENT", "geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    intersections["miles"] = intersections.geometry.length / 1609.344

    summary: dict[str, dict[str, object]] = {}
    for geoid, group in intersections.groupby("GEOID"):
        attainment = group.groupby("ATTAINMENT")["miles"].sum().to_dict()
        impaired_miles = attainment.get("Not Supporting", 0.0) + attainment.get("Not Supporting (Evaluated)", 0.0)
        full_miles = attainment.get("Fully Supporting", 0.0) + attainment.get("Fully Supporting (Evaluated)", 0.0)
        not_assessed = attainment.get("Not Assessed", 0.0)
        other = attainment.get("Threatened", 0.0)
        total = group["miles"].sum()

        top_waterbodies = (
            group.groupby("ASSESSME_1")["miles"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
            .index.tolist()
        )
        impaired_group = group[group["ATTAINMENT"].astype(str).str.contains("Not Supporting", na=False)].copy()
        cause_miles: dict[str, float] = {}
        cause_labels: dict[str, str] = {}
        cause_units: dict[str, set[str]] = {}

        for row in impaired_group.itertuples():
            waterbody = str(row.ASSESSME_1)
            for cause in _infer_impairment_causes(row.ASSESSMENT):
                cause_key = cause["cause"]
                cause_labels[cause_key] = cause["label"]
                cause_miles[cause_key] = cause_miles.get(cause_key, 0.0) + float(row.miles)
                cause_units.setdefault(cause_key, set()).add(waterbody)

        impairment_causes = [
            {
                "cause": cause_key,
                "label": cause_labels[cause_key],
                "miles": round(cause_miles[cause_key], 1),
                "assessmentUnits": len(cause_units.get(cause_key, set())),
            }
            for cause_key in sorted(cause_miles, key=lambda key: (-cause_miles[key], cause_labels[key]))
        ][:6]

        sample_impairments: list[dict[str, object]] = []
        if not impaired_group.empty:
            top_impaired_names = (
                impaired_group.groupby("ASSESSME_1")["miles"]
                .sum()
                .sort_values(ascending=False)
                .head(5)
                .index.tolist()
            )
            for name in top_impaired_names:
                subset = impaired_group[impaired_group["ASSESSME_1"] == name]
                cause_lookup: dict[str, str] = {}
                for assessment in subset["ASSESSMENT"].tolist():
                    for cause in _infer_impairment_causes(assessment):
                        cause_lookup[cause["cause"]] = cause["label"]
                sample_impairments.append(
                    {
                        "waterbody": name,
                        "status": ", ".join(sorted(subset["ATTAINMENT"].dropna().astype(str).unique())),
                        "causes": sorted(cause_lookup.values()),
                    }
                )

        categories = [
            {
                "category": key,
                "label": ATTAINMENT_LABELS.get(key, key),
                "miles": round(value, 1),
            }
            for key, value in sorted(attainment.items())
            if value > 0
        ]

        summary[str(geoid)] = {
            "reportingCycle": "2026",
            "impairedAssessmentUnits": int(group["ASSESSME_1"].nunique()),
            "impairedRiverMiles": round(impaired_miles, 1),
            "fullAttainmentRiverMiles": round(full_miles, 1),
            "notAssessedRiverMiles": round(not_assessed, 1),
            "otherAssessedRiverMiles": round(other, 1),
            "totalRiverMiles": round(total, 1),
            "attainmentCategories": categories,
            "impairmentCauses": impairment_causes,
            "sampleImpairments": sample_impairments,
            "sampleWaterbodies": top_waterbodies,
        }

    return summary


def summarize_monitoring_by_county(stations: gpd.GeoDataFrame) -> dict[str, dict[str, object]]:
    frame = stations.copy()
    frame["county_name"] = frame["COUNTY"].astype(str).str.replace(" County", "", regex=False)
    grouped = (
        frame.groupby("county_name")
        .agg(
            monitoringStations=("STATION_ID", "nunique"),
            riverStations=("WATER_TYPE", lambda values: int((values == "River/Stream").sum())),
        )
        .reset_index()
    )
    return grouped.set_index("county_name").to_dict(orient="index")


def summarize_permits_by_county(permits: gpd.GeoDataFrame) -> dict[str, dict[str, object]]:
    frame = permits.copy()
    frame["county_name"] = frame["COUNTY"].astype(str).str.replace(" County", "", regex=False)
    grouped = (
        frame.groupby("county_name")
        .agg(
            activePermits=("PERMIT_NUM", "count"),
            permittees=("PERMITTEE_", "nunique"),
            permittedFlow=("PERMIT_FLO", lambda values: round(pd.to_numeric(values, errors="coerce").fillna(0).sum(), 3)),
        )
        .reset_index()
    )
    return grouped.set_index("county_name").to_dict(orient="index")


def summarize_scenic_rivers_by_county(
    counties: gpd.GeoDataFrame,
    scenic_rivers: gpd.GeoDataFrame,
) -> dict[str, dict[str, object]]:
    county_proj = counties[["GEOID", "geometry"]].to_crs(AREA_CRS)
    scenic_proj = scenic_rivers[["NAME", "DESIGNATIO", "geometry"]].to_crs(AREA_CRS)
    intersections = gpd.overlay(county_proj, scenic_proj, how="intersection", keep_geom_type=False)
    intersections["miles"] = intersections.geometry.length / 1609.344

    summary: dict[str, dict[str, object]] = {}
    for geoid, group in intersections.groupby("GEOID"):
        summary[str(geoid)] = {
            "scenicRiverMiles": round(group["miles"].sum(), 1),
            "scenicRiverSegments": int(group["NAME"].nunique()),
            "scenicRiverNames": group.groupby("NAME")["miles"].sum().sort_values(ascending=False).head(4).index.tolist(),
        }
    return summary


def summarize_water_service_areas_by_county(
    counties: gpd.GeoDataFrame,
    service_areas: gpd.GeoDataFrame,
) -> dict[str, dict[str, object]]:
    county_proj = counties[["GEOID", "geometry"]].to_crs(AREA_CRS)
    service_proj = service_areas[["PWSID", "MA_NAME", "geometry"]].to_crs(AREA_CRS)
    intersections = gpd.overlay(county_proj, service_proj, how="intersection")
    intersections["area"] = intersections.geometry.area

    summary: dict[str, dict[str, object]] = {}
    for geoid, group in intersections.groupby("GEOID"):
        top_systems = (
            group.groupby("MA_NAME")["area"]
            .sum()
            .sort_values(ascending=False)
            .head(4)
            .index.tolist()
        )
        summary[str(geoid)] = {
            "serviceAreaCount": int(group["PWSID"].nunique()),
            "serviceAreaNames": top_systems,
        }
    return summary


def compute_county_metric_ranks(
    counties: gpd.GeoDataFrame,
    acs_lookup: dict[str, dict[str, object]],
    justice40_lookup: dict[str, dict[str, object]],
    impairment_lookup: dict[str, dict[str, object]],
    monitoring_lookup: dict[str, dict[str, object]],
    permit_lookup: dict[str, dict[str, object]],
    scenic_lookup: dict[str, dict[str, object]],
    water_service_lookup: dict[str, dict[str, object]],
) -> dict[str, dict[str, dict[str, object]]]:
    metric_values: dict[str, list[tuple[str, float]]] = {key: [] for key in RANKING_BASIS}

    for county in counties.itertuples():
        geoid = str(county.GEOID)
        acs_row = acs_lookup[geoid]
        justice40_row = justice40_lookup.get(
            geoid,
            {"tract_count": 0, "disadvantaged_tracts": 0, "water_flags": 0, "climate_flags": 0},
        )
        impairment_row = impairment_lookup.get(
            geoid,
            {
                "impairedRiverMiles": 0.0,
                "fullAttainmentRiverMiles": 0.0,
                "notAssessedRiverMiles": 0.0,
                "otherAssessedRiverMiles": 0.0,
            },
        )
        monitoring_row = monitoring_lookup.get(county.NAME, {})
        permit_row = permit_lookup.get(county.NAME, {})
        scenic_row = scenic_lookup.get(geoid, {})
        water_service_row = water_service_lookup.get(geoid, {})

        tract_count = int(justice40_row.get("tract_count", 0))
        disadvantaged_pct = _percentage(int(justice40_row.get("disadvantaged_tracts", 0)), tract_count)
        water_stress_pct = _percentage(int(justice40_row.get("water_flags", 0)), tract_count)
        climate_stress_pct = _percentage(int(justice40_row.get("climate_flags", 0)), tract_count)

        metric_values["population"].append((geoid, float(acs_row["population"])))
        metric_values["povertyRate"].append((geoid, round(float(acs_row["poverty_rate"]), 1)))
        metric_values["disadvantagedTractShare"].append((geoid, disadvantaged_pct))
        metric_values["impairedRiverMiles"].append((geoid, float(impairment_row.get("impairedRiverMiles", 0.0))))
        metric_values["fullAttainmentRiverMiles"].append((geoid, float(impairment_row.get("fullAttainmentRiverMiles", 0.0))))
        metric_values["notAssessedRiverMiles"].append((geoid, float(impairment_row.get("notAssessedRiverMiles", 0.0))))
        metric_values["otherAssessedRiverMiles"].append((geoid, float(impairment_row.get("otherAssessedRiverMiles", 0.0))))
        metric_values["monitoringStations"].append((geoid, float(monitoring_row.get("monitoringStations", 0))))
        metric_values["activePermits"].append((geoid, float(permit_row.get("activePermits", 0))))
        metric_values["scenicRiverMiles"].append((geoid, float(scenic_row.get("scenicRiverMiles", 0.0))))
        metric_values["waterServiceAreas"].append((geoid, float(water_service_row.get("serviceAreaCount", 0))))
        metric_values["waterStressTractShare"].append((geoid, water_stress_pct))
        metric_values["climateStressTractShare"].append((geoid, climate_stress_pct))

    total = len(counties)
    metric_rank_lookup = {metric: _rank_values(values) for metric, values in metric_values.items()}
    county_ranks: dict[str, dict[str, dict[str, object]]] = {}

    for county in counties.itertuples():
        geoid = str(county.GEOID)
        county_ranks[geoid] = {
            metric: _rank_entry(metric_rank_lookup[metric][geoid], total, RANKING_BASIS[metric])
            for metric in metric_values
        }

    return county_ranks


def _feature_collection(frame: gpd.GeoDataFrame) -> dict[str, object]:
    if frame.empty:
        return {"type": "FeatureCollection", "features": []}
    return json.loads(frame.to_json())


def _county_viewport_frame(county_frame: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    county_wgs84 = county_frame.to_crs("EPSG:4326")
    minx, miny, maxx, maxy = county_wgs84.total_bounds
    width = maxx - minx
    height = maxy - miny
    base_width = width + 2 * max(width * POLYGON_VIEWPORT_FIT_PADDING_RATIO, 0.015)
    base_height = height + 2 * max(height * POLYGON_VIEWPORT_FIT_PADDING_RATIO, 0.015)
    target_width = base_width
    target_height = base_height

    for aspect_ratio in POLYGON_VIEWPORT_ASPECT_RATIOS:
        if base_width / base_height < aspect_ratio:
            view_width = base_height * aspect_ratio
            view_height = base_height
        else:
            view_width = base_width
            view_height = base_width / aspect_ratio
        target_width = max(target_width, view_width * POLYGON_VIEWPORT_PIXEL_PADDING_FACTOR)
        target_height = max(target_height, view_height * POLYGON_VIEWPORT_PIXEL_PADDING_FACTOR)

    lon_padding = max((target_width - width) / 2, POLYGON_VIEWPORT_MIN_PADDING_DEGREES)
    lat_padding = max((target_height - height) / 2, POLYGON_VIEWPORT_MIN_PADDING_DEGREES)
    return gpd.GeoDataFrame(
        geometry=[box(minx - lon_padding, miny - lat_padding, maxx + lon_padding, maxy + lat_padding)],
        crs="EPSG:4326",
    )


def _clip_to_frame(
    source: gpd.GeoDataFrame,
    clip_frame: gpd.GeoDataFrame,
    *,
    simplify_meters: float,
    keep_columns: list[str],
) -> gpd.GeoDataFrame:
    clip_proj = clip_frame.to_crs(AREA_CRS)
    source_proj = source.to_crs(AREA_CRS)
    clip_geometry = clip_proj.geometry.iloc[0]
    matches = source_proj.sindex.query(clip_geometry, predicate="intersects")
    if len(matches) == 0:
        return source.iloc[0:0][keep_columns + ["geometry"]].copy()

    subset = source_proj.iloc[matches][keep_columns + ["geometry"]].copy()
    clipped = gpd.clip(subset, clip_proj)
    if clipped.empty:
        return clipped

    clipped["geometry"] = clipped.geometry.simplify(simplify_meters, preserve_topology=True)
    clipped = clipped[~clipped.geometry.is_empty & clipped.geometry.notnull()].copy()
    return clipped.to_crs("EPSG:4326")


def _clip_to_county(
    source: gpd.GeoDataFrame,
    county_frame: gpd.GeoDataFrame,
    *,
    simplify_meters: float,
    keep_columns: list[str],
) -> gpd.GeoDataFrame:
    return _clip_to_frame(
        source,
        county_frame,
        simplify_meters=simplify_meters,
        keep_columns=keep_columns,
    )


def _clip_to_county_viewport(
    source: gpd.GeoDataFrame,
    county_frame: gpd.GeoDataFrame,
    *,
    simplify_meters: float,
    keep_columns: list[str],
) -> gpd.GeoDataFrame:
    return _clip_to_frame(
        source,
        _county_viewport_frame(county_frame),
        simplify_meters=simplify_meters,
        keep_columns=keep_columns,
    )


def write_county_map_payloads(
    counties: gpd.GeoDataFrame,
    huc8: gpd.GeoDataFrame,
    house: gpd.GeoDataFrame,
    senate: gpd.GeoDataFrame,
    congress: gpd.GeoDataFrame,
    rivers: gpd.GeoDataFrame,
    roads: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
    towns: gpd.GeoDataFrame,
    impairment: gpd.GeoDataFrame,
) -> None:
    roads = roads.copy()
    roads["style"] = roads["fclass"].map(ROAD_STYLES)
    roads = roads[roads["style"].notnull()].copy()

    river_lines = rivers.copy()
    river_lines["label_name"] = river_lines["label_name"].fillna(river_lines["river_name"])

    impairment_lines = impairment[impairment["WATER_TYPE"] == "RIVER"].copy()
    impairment_lines["status"] = impairment_lines["ATTAINMENT"].fillna("Unknown")
    impairment_lines["waterbody"] = impairment_lines["ASSESSME_1"].fillna("Unnamed waterbody")
    impairment_lines["impairment_causes"] = impairment_lines.apply(
        lambda row: "; ".join(cause["label"] for cause in _infer_impairment_causes(row["ASSESSMENT"]))
        if "Not Supporting" in str(row["ATTAINMENT"])
        else "",
        axis=1,
    )

    place_frames: list[gpd.GeoDataFrame] = []
    for frame, kind in [(cities.copy(), "city"), (towns.copy(), "town")]:
        item = frame[frame["name"].notnull()].copy()
        item["kind"] = kind
        item["geometry"] = item.geometry.representative_point()
        place_frames.append(item[["name", "kind", "geometry"]])
    places = pd.concat(place_frames, ignore_index=True)
    places = gpd.GeoDataFrame(places, geometry="geometry", crs="EPSG:4326")

    for county in counties.itertuples():
        county_frame = counties[counties["GEOID"] == county.GEOID][["GEOID", "NAME", "geometry"]].copy()

        county_outline = county_frame.to_crs(AREA_CRS).copy()
        county_outline["geometry"] = county_outline.geometry.simplify(120, preserve_topology=True)
        county_outline = county_outline.to_crs("EPSG:4326")
        rivers_layer = _clip_to_county(river_lines, county_frame, simplify_meters=140, keep_columns=["river_name", "label_name", "stroke_cla"])
        roads_layer = _clip_to_county(roads, county_frame, simplify_meters=140, keep_columns=["name", "ref", "style"])
        impairment_layer = _clip_to_county(
            impairment_lines,
            county_frame,
            simplify_meters=90,
            keep_columns=["status", "waterbody", "impairment_causes"],
        )
        watershed_layer = _clip_to_county_viewport(
            huc8,
            county_frame,
            simplify_meters=180,
            keep_columns=["huc8", "name", "areasqkm"],
        )
        senate_layer = _clip_to_county_viewport(
            senate.rename(columns={"DISTRICT": "district"}),
            county_frame,
            simplify_meters=140,
            keep_columns=["district"],
        )
        house_layer = _clip_to_county_viewport(
            house.rename(columns={"DISTRICT": "district"}),
            county_frame,
            simplify_meters=140,
            keep_columns=["district"],
        )
        congress_layer = _clip_to_county_viewport(
            congress.rename(columns={"DISTRICT": "district"}),
            county_frame,
            simplify_meters=140,
            keep_columns=["district"],
        )

        place_ids = places.sindex.query(county_frame.to_crs("EPSG:4326").geometry.iloc[0], predicate="intersects")
        places_layer = places.iloc[place_ids].copy()
        if not places_layer.empty:
            kind_rank = {"city": 0, "town": 1}
            places_layer["rank"] = places_layer["kind"].map(kind_rank).fillna(2)
            places_layer = places_layer.sort_values(["rank", "name"]).drop_duplicates(subset=["name"]).head(12)
            places_layer = places_layer.drop(columns=["rank"])

        payload = {
            "slug": county.slug,
            "name": county.NAME,
            "county": _feature_collection(county_outline),
            "rivers": _feature_collection(rivers_layer),
            "impairment": _feature_collection(impairment_layer),
            "roads": _feature_collection(roads_layer),
            "places": _feature_collection(places_layer),
            "watersheds": _feature_collection(watershed_layer),
            "districts": {
                "senate": _feature_collection(senate_layer),
                "house": _feature_collection(house_layer),
                "congressional": _feature_collection(congress_layer),
            },
        }

        (COUNTY_MAPS_DIR / f"{county.slug}.json").write_text(
            json.dumps(payload, separators=(",", ":")),
            encoding="utf8",
        )


def build_county_payload(
    *,
    county,
    region: str,
    focus: str,
    is_featured: bool,
    acs_row: dict[str, object],
    justice40_row: dict[str, object],
    impairment_row: dict[str, object],
    monitoring_row: dict[str, object],
    permit_row: dict[str, object],
    scenic_row: dict[str, object],
    water_service_row: dict[str, object],
    metric_ranks: dict[str, dict[str, object]],
    huc8_names: list[str],
    legislative: list[str],
    congressional: list[str],
    build_date: str,
) -> dict[str, object]:
    tract_count = int(justice40_row.get("tract_count", 0))
    disadvantaged_tracts = int(justice40_row.get("disadvantaged_tracts", 0))
    disadvantaged_pct = _percentage(disadvantaged_tracts, tract_count)
    water_stress_tracts = int(justice40_row.get("water_flags", 0))
    climate_stress_tracts = int(justice40_row.get("climate_flags", 0))
    water_stress_pct = _percentage(water_stress_tracts, tract_count)
    climate_stress_pct = _percentage(climate_stress_tracts, tract_count)

    scenic_names = scenic_row.get("scenicRiverNames", [])
    service_names = water_service_row.get("serviceAreaNames", [])

    return {
        "slug": county.slug,
        "name": county.NAME,
        "region": region,
        "population": int(acs_row["population"]),
        "buildDate": build_date,
        "prototypeStatus": {
            "label": "Featured county page" if is_featured else "Statewide county summary",
            "coverageNote": (
                "This county is part of the featured prototype cohort and includes more intentional narrative framing."
                if is_featured
                else "This county page is generated from statewide contracts so every Tennessee county has baseline environmental and civic context."
            ),
            "availableFeatures": [
                "County overview",
                "Indicator cards with definitions and caveats",
                "Statewide rank comparisons",
                "Water and climate stress rollups",
                "2026 impairment summary",
                "Justice40 screening summary",
                "Monitoring, permits, and scenic river context",
            ],
        },
        "isFeatured": is_featured,
        "watersheds": huc8_names[:4],
        "legislativeDistricts": legislative,
        "congressionalDistricts": congressional,
        "streamMiles": {
            "impaired": impairment_row["impairedRiverMiles"],
            "fullAttainment": impairment_row["fullAttainmentRiverMiles"],
            "notAssessed": impairment_row["notAssessedRiverMiles"],
            "otherAssessed": impairment_row["otherAssessedRiverMiles"],
            "total": impairment_row["totalRiverMiles"],
        },
        "rankings": metric_ranks,
        "attainmentCategories": impairment_row["attainmentCategories"],
        "impairmentSummary": (
            f"The local 2026 303(d) county summary shows about {impairment_row['impairedRiverMiles']:.1f} river miles in not supporting categories, "
            f"{impairment_row['fullAttainmentRiverMiles']:.1f} fully supporting miles, and {impairment_row['notAssessedRiverMiles']:.1f} not assessed miles in {county.NAME} County."
        ),
        "impairmentCauses": impairment_row.get("impairmentCauses", []),
        "sampleImpairments": impairment_row.get("sampleImpairments", []),
        "sampleWaterbodies": impairment_row["sampleWaterbodies"],
        "cejstSummary": (
            f"Using the local Justice40 / CEJST tract snapshot, {disadvantaged_tracts} of {tract_count} census tracts in "
            f"{county.NAME} County are flagged as disadvantaged ({disadvantaged_pct:.1f}%). "
            f"{water_stress_tracts} {_tract_word(water_stress_tracts)} carry the water and wastewater stress flag, "
            f"and {climate_stress_tracts} {_tract_word(climate_stress_tracts)} carry the climate stress flag."
        ),
        "stressSummary": {
            "sourceDataset": "Justice40 / CEJST local snapshot",
            "updatedAt": build_date,
            "caveat": (
                "Water stressed and climate stressed are local labels for CEJST category flags. "
                "They are screening indicators, not direct measurements or regulatory determinations."
            ),
            "water": {
                "label": "Water stressed tracts",
                "tracts": water_stress_tracts,
                "tractCount": tract_count,
                "percent": water_stress_pct,
                "stateRank": metric_ranks["waterStressTractShare"],
                "description": (
                    "Census tracts flagged in the CEJST water and wastewater category in the local snapshot."
                ),
            },
            "climate": {
                "label": "Climate stressed tracts",
                "tracts": climate_stress_tracts,
                "tractCount": tract_count,
                "percent": climate_stress_pct,
                "stateRank": metric_ranks["climateStressTractShare"],
                "description": "Census tracts flagged in the CEJST climate category in the local snapshot.",
            },
        },
        "overview": (
            f"{county.NAME} County is represented as a {region} county summary focused on {focus}. "
            f"It intersects {', '.join(huc8_names[:3]) if huc8_names else 'multiple watershed areas'} and overlaps "
            f"{len(legislative)} state legislative district labels plus {len(congressional)} congressional district labels."
        ),
        "getInvolved": [
            f"Review county and municipal agendas in {county.NAME} County for stormwater, wastewater, landfill, quarry, and land-use decisions.",
            "Use the county page to connect statewide indicators with local watersheds, monitoring stations, and source notes.",
            f"Check local monitoring and permit context alongside {'; '.join(service_names[:2]) if service_names else 'public water system service areas'} for community-specific follow-up.",
        ],
        "indicators": [
            {
                "key": "acs-pop",
                "label": "Population",
                "value": f"{int(acs_row['population']):,}",
                "definition": "ACS 5-year total county population.",
                "caveat": "ACS estimates should be read as broad county context rather than precise local conditions.",
                "sourceDataset": "ACS indicators",
                "updatedAt": build_date,
                "stateRank": metric_ranks["population"],
            },
            {
                "key": "acs-poverty",
                "label": "Poverty rate",
                "value": f"{acs_row['poverty_rate']:.1f}%",
                "definition": "Share of people below the poverty level based on ACS table B17001.",
                "caveat": "County-wide rates can hide tract-level variation.",
                "sourceDataset": "ACS indicators",
                "updatedAt": build_date,
                "stateRank": metric_ranks["povertyRate"],
            },
            {
                "key": "j40-disadvantaged",
                "label": "Disadvantaged tracts",
                "value": f"{disadvantaged_pct:.1f}%",
                "definition": "Share of county tracts flagged as disadvantaged in the local Justice40 / CEJST tract snapshot.",
                "caveat": "Justice40 is a screening context, not a final judgment about community need.",
                "sourceDataset": "Justice40 / CEJST local snapshot",
                "updatedAt": build_date,
                "stateRank": metric_ranks["disadvantagedTractShare"],
            },
            {
                "key": "impaired-river-miles",
                "label": "Impaired river miles",
                "value": f"{impairment_row['impairedRiverMiles']:.1f}",
                "definition": "Approximate river miles intersecting county boundaries in 2026 not supporting impairment categories.",
                "caveat": "Line segments are spatially intersected with county boundaries, so shared waters can contribute to multiple counties.",
                "sourceDataset": "2026 303(d) impairment layer",
                "updatedAt": build_date,
                "stateRank": metric_ranks["impairedRiverMiles"],
            },
            {
                "key": "monitoring-stations",
                "label": "Monitoring stations",
                "value": str(int(monitoring_row.get("monitoringStations", 0))),
                "definition": "Distinct DWR water-quality monitoring stations associated with the county.",
                "caveat": "Station presence does not by itself indicate adequate monitoring coverage or condition.",
                "sourceDataset": "DWR monitoring stations",
                "updatedAt": build_date,
                "stateRank": metric_ranks["monitoringStations"],
            },
            {
                "key": "active-permits",
                "label": "Active water permits",
                "value": str(int(permit_row.get("activePermits", 0))),
                "definition": "Count of active permitted features associated with the county in the local permit layer.",
                "caveat": "Permit counts mix facility types and do not directly measure pollutant load or compliance status.",
                "sourceDataset": "Active permitted features",
                "updatedAt": build_date,
                "stateRank": metric_ranks["activePermits"],
            },
            {
                "key": "scenic-river-miles",
                "label": "Scenic river miles",
                "value": f"{scenic_row.get('scenicRiverMiles', 0.0):.1f}",
                "definition": "Approximate miles of designated Tennessee scenic river segments intersecting the county.",
                "caveat": "This captures designated segments only, not broader watershed influence.",
                "sourceDataset": "Tennessee scenic rivers",
                "updatedAt": build_date,
                "stateRank": metric_ranks["scenicRiverMiles"],
            },
        ],
        "monitoringSummary": {
            "stations": int(monitoring_row.get("monitoringStations", 0)),
            "riverStations": int(monitoring_row.get("riverStations", 0)),
        },
        "permittingSummary": {
            "activePermits": int(permit_row.get("activePermits", 0)),
            "uniquePermittees": int(permit_row.get("permittees", 0)),
            "permittedFlow": float(permit_row.get("permittedFlow", 0.0)),
        },
        "scenicRiverSummary": {
            "miles": float(scenic_row.get("scenicRiverMiles", 0.0)),
            "segments": int(scenic_row.get("scenicRiverSegments", 0)),
            "names": scenic_names,
        },
        "waterServiceSummary": {
            "serviceAreas": int(water_service_row.get("serviceAreaCount", 0)),
            "names": service_names,
        },
    }


def write_processed_summary(
    counties: gpd.GeoDataFrame,
    acs: pd.DataFrame,
    justice40: gpd.GeoDataFrame,
    impairment: gpd.GeoDataFrame,
    monitoring_stations: gpd.GeoDataFrame,
    active_permits: gpd.GeoDataFrame,
    scenic_rivers: gpd.GeoDataFrame,
    water_service_areas: gpd.GeoDataFrame,
    region_lookup: dict[str, str],
    watershed_labels: dict[str, list[str]],
    senate_labels: dict[str, list[str]],
    house_labels: dict[str, list[str]],
    congressional_labels: dict[str, list[str]],
    *,
    build_date: str,
) -> None:
    county_index: list[dict[str, object]] = []
    search_index: list[dict[str, str]] = []

    acs_lookup = acs.set_index("geoid").to_dict(orient="index")
    justice40_lookup = summarize_justice40_by_county(justice40)
    impairment_lookup = summarize_impairment_by_county(counties, impairment)
    monitoring_lookup = summarize_monitoring_by_county(monitoring_stations)
    permit_lookup = summarize_permits_by_county(active_permits)
    scenic_lookup = summarize_scenic_rivers_by_county(counties, scenic_rivers)
    water_service_lookup = summarize_water_service_areas_by_county(counties, water_service_areas)
    metric_rank_lookup = compute_county_metric_ranks(
        counties,
        acs_lookup,
        justice40_lookup,
        impairment_lookup,
        monitoring_lookup,
        permit_lookup,
        scenic_lookup,
        water_service_lookup,
    )

    for county in counties.itertuples():
        region = region_lookup.get(county.GEOID, "Tennessee")
        featured = FEATURED_COUNTIES.get(county.GEOID)
        is_featured = featured is not None
        focus = (
            featured["focus"]
            if featured
            else "county-scale watershed conditions, public-interest infrastructure context, and environmental screening indicators"
        )

        acs_row = acs_lookup[county.GEOID]
        justice40_row = justice40_lookup.get(
            county.GEOID,
            {"tract_count": 0, "disadvantaged_tracts": 0, "water_flags": 0, "climate_flags": 0},
        )
        impairment_row = impairment_lookup.get(
            county.GEOID,
            {
                "reportingCycle": "2026",
                "impairedAssessmentUnits": 0,
                "impairedRiverMiles": 0.0,
                "fullAttainmentRiverMiles": 0.0,
                "notAssessedRiverMiles": 0.0,
                "otherAssessedRiverMiles": 0.0,
                "totalRiverMiles": 0.0,
                "attainmentCategories": [],
                "impairmentCauses": [],
                "sampleImpairments": [],
                "sampleWaterbodies": [],
            },
        )
        monitoring_row = monitoring_lookup.get(county.NAME, {})
        permit_row = permit_lookup.get(county.NAME, {})
        scenic_row = scenic_lookup.get(county.GEOID, {})
        water_service_row = water_service_lookup.get(county.GEOID, {})
        metric_ranks = metric_rank_lookup[str(county.GEOID)]
        huc8_names = watershed_labels.get(county.GEOID, [])
        legislative = house_labels.get(county.GEOID, []) + senate_labels.get(county.GEOID, [])
        congressional = congressional_labels.get(county.GEOID, [])

        county_index.append(
            {
                "slug": county.slug,
                "name": county.NAME,
                "region": f"{region} Tennessee",
                "summary": (
                    f"{county.NAME} County intersects {len(huc8_names)} HUC8 watersheds and has "
                    f"{impairment_row['impairedRiverMiles']:.1f} locally summarized impaired river miles in the 2026 layer."
                ),
                "hasPage": True,
                "isFeatured": is_featured,
            }
        )
        search_index.append({"type": "county", "slug": county.slug, "label": f"{county.NAME} County"})

        county_payload = build_county_payload(
            county=county,
            region=f"{region} Tennessee",
            focus=focus,
            is_featured=is_featured,
            acs_row=acs_row,
            justice40_row=justice40_row,
            impairment_row=impairment_row,
            monitoring_row=monitoring_row,
            permit_row=permit_row,
            scenic_row=scenic_row,
            water_service_row=water_service_row,
            metric_ranks=metric_ranks,
            huc8_names=huc8_names,
            legislative=legislative,
            congressional=congressional,
            build_date=build_date,
        )

        (COUNTIES_DIR / f"{county.slug}.json").write_text(json.dumps(county_payload, indent=2), encoding="utf8")

    county_index.sort(key=lambda item: item["name"])
    search_index.sort(key=lambda item: item["label"])
    (COUNTIES_DIR / "index.json").write_text(json.dumps(county_index, indent=2), encoding="utf8")
    (SEARCH_DIR / "search-index.json").write_text(json.dumps(search_index, indent=2), encoding="utf8")


def write_metadata(*, build_date: str) -> None:
    sources = [
        {
            "dataset": "Tennessee counties",
            "purpose": "Base county geography for statewide navigation and county summary pages.",
            "sourceName": "Census TIGER/Line 2024 Counties",
            "sourceUrl": COUNTY_ZIP_URL,
            "refreshFrequency": "Annual",
            "lastUpdated": build_date,
            "notes": "Prototype exports a simplified Tennessee-only county layer from the national TIGER/Line shapefile.",
        },
        {
            "dataset": "HUC8 watersheds",
            "purpose": "Watershed context for county pages and overlay controls.",
            "sourceName": "USGS WBD MapServer layer 4",
            "sourceUrl": "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4",
            "refreshFrequency": "Periodic",
            "lastUpdated": build_date,
            "notes": "Prototype filters the official WBD subbasin layer to hydrologic units whose state list includes Tennessee.",
        },
        {
            "dataset": "Legislative districts",
            "purpose": "State and congressional district overlays and county overlap summaries.",
            "sourceName": "TNMap Legislative Districts service",
            "sourceUrl": TN_LEG_URL,
            "refreshFrequency": "Redistricting / official updates",
            "lastUpdated": build_date,
            "notes": "Prototype uses the Tennessee 2022 district service for senate, house, and congressional boundaries.",
        },
        {
            "dataset": "ACS indicators",
            "purpose": "County demographic and socioeconomic context.",
            "sourceName": "U.S. Census ACS 2024 5-year API",
            "sourceUrl": f"{ACS_URL}.html",
            "refreshFrequency": "Annual",
            "lastUpdated": build_date,
            "notes": "Prototype pulls population, median household income, and poverty-related values and writes them into county summary JSON.",
        },
        {
            "dataset": "Justice40 / CEJST local snapshot",
            "purpose": "County-level rollup of tract disadvantage, water stress, and climate stress flags.",
            "sourceName": "Harpeth Conservancy copy of ATP and Justice40 tract layer",
            "sourceUrl": str(JUSTICE40_PATH),
            "refreshFrequency": "Versioned snapshot",
            "lastUpdated": build_date,
            "notes": "Copied into the repo from the Harpeth Conservancy GIS workspace for stable local county-level aggregation of CEJST tract category flags.",
        },
        {
            "dataset": "2026 303(d) impairment layer",
            "purpose": "County-level river impairment summaries, inferred cause summaries, and sample waterbody names.",
            "sourceName": "Harpeth Conservancy copy of TDEC 2026 303(d) layer",
            "sourceUrl": str(IMPAIRMENT_2026_PATH),
            "refreshFrequency": "Assessment cycle",
            "lastUpdated": build_date,
            "notes": "River segments are intersected with county boundaries to estimate county-level impaired, fully supporting, and not assessed river miles. Cause summaries are inferred from the local assessment-rationale text when coded cause fields are unavailable.",
        },
        {
            "dataset": "EPA ATTAINS assessment geospatial layer",
            "purpose": "Interactive county-map overlay for impaired, good, and unassessed river status from EPA How's My Waterway / ATTAINS assessment data.",
            "sourceName": "EPA ATTAINS Assessment MapServer layer 1",
            "sourceUrl": "https://gispub.epa.gov/arcgis/rest/services/OW/ATTAINS_Assessment/MapServer/1",
            "refreshFrequency": "EPA service update cycle",
            "lastUpdated": build_date,
            "notes": "County maps query the public EPA geospatial service by county bounding box at runtime and display coded ATTAINS impairment causes when available. Maps fall back to the local 2026 303(d) layer if the service is unavailable.",
        },
        {
            "dataset": "DWR monitoring stations",
            "purpose": "Count county-associated water-quality monitoring stations.",
            "sourceName": "Harpeth Conservancy copy of Water Quality Monitoring Stations",
            "sourceUrl": str(MONITORING_STATIONS_PATH),
            "refreshFrequency": "Periodic",
            "lastUpdated": build_date,
            "notes": "Used to summarize monitoring presence by county.",
        },
        {
            "dataset": "TDEC DWR public water resources permits",
            "purpose": "Interactive county-map overlay differentiating active permit records from pending or incomplete permit records.",
            "sourceName": "TDEC DWR Public MapServer layer 1",
            "sourceUrl": "https://tdeconline.tn.gov/arcgis/rest/services/DWR_Public/MapServer/1",
            "refreshFrequency": "Weekly cache",
            "lastUpdated": build_date,
            "notes": "County maps use a static weekly cache generated from the public TDEC DWR MapServer. The browser falls back to the live service when a cache file is unavailable.",
        },
        {
            "dataset": "EPA ECHO CWA permit compliance",
            "purpose": "Interactive county-map overlay identifying CWA/NPDES permits with recent or current violation records.",
            "sourceName": "EPA ECHO CWA REST Services get_facilities and get_qid",
            "sourceUrl": "https://echodata.epa.gov/echo/cwa_rest_services.get_facilities",
            "refreshFrequency": "Weekly cache",
            "lastUpdated": build_date,
            "notes": "County maps load committed ECHO CWA violation cache files first. Weekly refreshes update those files when ECHO responds and leave the last good cache in place when the service is unavailable.",
        },
        {
            "dataset": "Active permitted features",
            "purpose": "Count county-associated active water permits.",
            "sourceName": "Harpeth Conservancy copy of Active Permitted Features",
            "sourceUrl": str(ACTIVE_PERMITS_PATH),
            "refreshFrequency": "Periodic",
            "lastUpdated": build_date,
            "notes": "Used to summarize permitted water features by county.",
        },
        {
            "dataset": "TNMap composite address locator",
            "purpose": "County-map address search and zoom-to-location behavior.",
            "sourceName": "TNMap Composite GeocodeServer",
            "sourceUrl": "https://tnmap.tn.gov/arcgis/rest/services/LOCATORS/TN_COMPOSITE/GeocodeServer",
            "refreshFrequency": "TNMap / E911 addressing update cycle",
            "lastUpdated": build_date,
            "notes": "Address searches are submitted from the client and filtered to the selected county bounding box before the map zooms to a result.",
        },
        {
            "dataset": "Tennessee scenic rivers",
            "purpose": "Show designated scenic river presence by county.",
            "sourceName": "Harpeth Conservancy copy of Scenic Rivers line layer",
            "sourceUrl": str(SCENIC_RIVERS_PATH),
            "refreshFrequency": "As designated",
            "lastUpdated": build_date,
            "notes": "Scenic river lines are intersected with counties to estimate scenic river miles by county.",
        },
        {
            "dataset": "Public water system service areas",
            "purpose": "Show how many public water service areas intersect each county.",
            "sourceName": "Harpeth Conservancy copy of Tennessee public water system service areas",
            "sourceUrl": str(WATER_SERVICE_AREAS_PATH),
            "refreshFrequency": "Periodic",
            "lastUpdated": build_date,
            "notes": "Polygon intersections are used to count overlapping service areas and identify the largest named systems by county.",
        },
    ]
    (METADATA_DIR / "data-sources.json").write_text(json.dumps(sources, indent=2), encoding="utf8")

    last_updated = {
        "county-pages": build_date,
        "acs": build_date,
        "justice40": build_date,
        "impairment-2026": build_date,
        "epa-attains": build_date,
        "watersheds": build_date,
        "districts": build_date,
        "monitoring": build_date,
        "tdec-dwr-public-permits": build_date,
        "epa-echo-cwa": build_date,
        "permits": build_date,
        "tnmap-locator": build_date,
        "scenic-rivers": build_date,
        "water-service-areas": build_date,
    }
    (METADATA_DIR / "last-updated.json").write_text(json.dumps(last_updated, indent=2), encoding="utf8")
