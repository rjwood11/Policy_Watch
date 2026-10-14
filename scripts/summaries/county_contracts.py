from __future__ import annotations

import json

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box

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
    PADUS_PROTECTION_MECHANISM_URL,
    SCENIC_RIVERS_PATH,
    SEARCH_DIR,
    TDEC_SERVICE_LINE_INVENTORY_URL,
    TDEC_SOLID_WASTE_PERMITS_URL,
    TDEC_WATER_SERVICE_AREAS_URL,
    TN_LEG_URL,
    WBD_HUC6_URL,
    WBD_HUC8_URL,
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

WATER_SOURCE_TYPE_LABELS = {
    "GW": "Groundwater",
    "GWP": "Purchased groundwater",
    "GU": "Groundwater under direct influence of surface water",
    "GUP": "Purchased groundwater under direct influence of surface water",
    "SW": "Surface water",
    "SWP": "Purchased surface water",
}

WATER_SOURCE_GROUPS = {
    "GW": "groundwater",
    "GWP": "groundwater",
    "GU": "mixed",
    "GUP": "mixed",
    "SW": "surface",
    "SWP": "surface",
}

SERVICE_LINE_COUNT_COLUMNS = {
    "Inventory_": "total_lines",
    "Lead": "lead_lines",
    "NonLead": "non_lead_lines",
    "GRR": "grr_lines",
    "Unknown": "unknown_lines",
}

WATER_OWNERSHIP_LABELS = {
    "F": "Federal",
    "L": "Local government",
    "P": "Private",
    "S": "State government",
}

PADUS_CATEGORY_GROUPS = {
    "Fee": "fee",
    "Easement": "easement",
    "Designation": "designation",
    "Proclamation": "planning",
    "Other": "other",
}

PADUS_OWNER_TYPE_LABELS = {
    "DESG": "Designation",
    "DIST": "Regional or special district",
    "FED": "Federal",
    "JNT": "Joint",
    "LOC": "Local government",
    "NGO": "Nonprofit",
    "PVT": "Private",
    "STAT": "State",
    "TRIB": "Tribal",
    "UNK": "Unknown",
}

PADUS_ACCESS_LABELS = {
    "OA": "Open access",
    "RA": "Restricted access",
    "XA": "Closed to public access",
    "UK": "Unknown public access",
}

PADUS_GAP_STATUS_LABELS = {
    "1": "GAP 1: biodiversity protection; natural disturbance maintained",
    "2": "GAP 2: biodiversity protection; natural disturbance may be suppressed",
    "3": "GAP 3: multiple-use conservation; extraction may occur",
    "4": "GAP 4: no known biodiversity protection mandate",
}

LANDFILL_TYPE_ORDER = {
    "CLASS I": 0,
    "CLASS II": 1,
    "CLASS III": 2,
    "CLASS IV": 3,
    "COAL ASH": 4,
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


def _unique_text(values: pd.Series, *, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []

    for value in values:
        text = str(value).strip() if pd.notna(value) else ""
        if not text or text.lower() == "nan" or text in seen:
            continue
        seen.add(text)
        items.append(text)
        if limit is not None and len(items) >= limit:
            break

    return items


def _first_text(values: pd.Series, default: str = "") -> str:
    items = _unique_text(values, limit=1)
    return items[0] if items else default


def _joined_text(values: pd.Series, *, limit: int | None = None) -> str:
    return "; ".join(_unique_text(values, limit=limit))


def _counted_text(values: pd.Series, *, type_order: dict[str, int] | None = None) -> str:
    counts = values.dropna().astype(str).str.strip()
    counts = counts[counts != ""].value_counts()
    if counts.empty:
        return ""

    labels = list(counts.index)
    if type_order is not None:
        labels.sort(key=lambda value: (type_order.get(value, 99), value))
    else:
        labels.sort()

    return "; ".join(f"{label} ({int(counts[label])})" for label in labels)


def _arcgis_latest_date(values: pd.Series) -> str:
    numeric_values = pd.to_numeric(values, errors="coerce")
    dates = pd.to_datetime(numeric_values, unit="ms", errors="coerce").dropna()
    if dates.empty:
        return ""
    return str(dates.max().date())


def _prepare_service_line_inventory(inventory: gpd.GeoDataFrame) -> pd.DataFrame:
    columns = ["pwsid", *SERVICE_LINE_COUNT_COLUMNS.values(), "service_line_inventory_status"]
    if inventory.empty or "PWSID" not in inventory.columns:
        return pd.DataFrame(columns=columns)

    frame = inventory.copy()
    frame["pwsid"] = frame["PWSID"].fillna("").astype(str).str.strip().str.upper()
    frame = frame[frame["pwsid"] != ""].copy()
    if frame.empty:
        return pd.DataFrame(columns=columns)

    source_count_columns: list[str] = []
    for source_column, output_column in SERVICE_LINE_COUNT_COLUMNS.items():
        if source_column in frame.columns:
            frame[output_column] = pd.to_numeric(frame[source_column], errors="coerce").round()
            source_count_columns.append(output_column)
        else:
            frame[output_column] = pd.NA

    if source_count_columns:
        frame = frame[frame[source_count_columns].notna().any(axis=1)].copy()
    else:
        frame = frame.iloc[0:0].copy()
    if frame.empty:
        return pd.DataFrame(columns=columns)

    component_columns = ["lead_lines", "non_lead_lines", "grr_lines", "unknown_lines"]
    calculated_total = frame[component_columns].fillna(0).sum(axis=1).round()
    frame["total_lines"] = frame["total_lines"].fillna(calculated_total)
    for output_column in SERVICE_LINE_COUNT_COLUMNS.values():
        frame[output_column] = frame[output_column].fillna(0).astype(int)
    frame["service_line_inventory_status"] = "available"

    return frame[columns].groupby("pwsid", as_index=False).agg(
        {
            "total_lines": "max",
            "lead_lines": "max",
            "non_lead_lines": "max",
            "grr_lines": "max",
            "unknown_lines": "max",
            "service_line_inventory_status": "first",
        }
    )


def _landfill_status_group(action: object) -> str:
    text = str(action or "").strip().lower()
    if text == "active" or text.endswith("-active") or text.endswith(" -active"):
        return "active"
    if text in {"pending", "incomplete"}:
        return "pending"
    return "inactive"


def _prepare_landfill_locations(landfills: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if landfills.empty:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    source = landfills.copy()
    source = source[source.geometry.notnull()].copy()
    if source.empty:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    if source.crs is None:
        source = source.set_crs("EPSG:4326")
    source = source.to_crs("EPSG:4326")
    source["longitude"] = pd.to_numeric(source["LONGITUDE"], errors="coerce")
    source["latitude"] = pd.to_numeric(source["LATITUDE"], errors="coerce")
    point_mask = source.geometry.geom_type == "Point"
    source.loc[source["longitude"].isna() & point_mask, "longitude"] = source.loc[
        source["longitude"].isna() & point_mask
    ].geometry.x
    source.loc[source["latitude"].isna() & point_mask, "latitude"] = source.loc[
        source["latitude"].isna() & point_mask
    ].geometry.y
    source = source[source["longitude"].notna() & source["latitude"].notna()].copy()
    if source.empty:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    source["site_id_text"] = pd.to_numeric(source["SITE_ID"], errors="coerce").apply(
        lambda value: str(int(value)) if pd.notna(value) else ""
    )
    source["site_key"] = source["site_id_text"]
    missing_key = source["site_key"] == ""
    source.loc[missing_key, "site_key"] = source.loc[missing_key].apply(
        lambda row: "|".join(
            [
                f"{float(row['longitude']):.6f}",
                f"{float(row['latitude']):.6f}",
                str(row.get("PERMITTEE_NAME") or "").strip(),
                str(row.get("SITE_LOCATION") or "").strip(),
            ]
        ),
        axis=1,
    )
    source["status_group"] = source["PERMITTING_ACTION"].map(_landfill_status_group)
    source["status_priority"] = source["status_group"].map({"active": 0, "pending": 1, "inactive": 2}).fillna(3)
    source["issuance_sort"] = pd.to_numeric(source["ISSUANCE_DATE"], errors="coerce").fillna(0)
    source = source.sort_values(["site_key", "status_priority", "issuance_sort"], ascending=[True, True, False])

    records: list[dict[str, object]] = []
    for index, (site_key, group) in enumerate(source.groupby("site_key", sort=False), start=1):
        representative = group.iloc[0]
        statuses = set(group["status_group"].astype(str))
        status_group = "active" if "active" in statuses else "pending" if "pending" in statuses else "inactive"
        status_label = {
            "active": "Active landfill permit record",
            "pending": "Pending landfill permit record",
            "inactive": "Inactive or historic landfill permit record",
        }[status_group]
        permit_numbers = _unique_text(group["PERMIT_NUMBER"], limit=10)
        unique_permit_count = len(_unique_text(group["PERMIT_NUMBER"]))
        permit_types = _unique_text(group["PERMIT_TYPE"])
        permit_types.sort(key=lambda value: (LANDFILL_TYPE_ORDER.get(value, 99), value))
        permittee_names = _unique_text(group["PERMITTEE_NAME"], limit=5)
        longitude = float(representative["longitude"])
        latitude = float(representative["latitude"])

        records.append(
            {
                "landfill_id": str(site_key) if site_key else f"landfill-{index}",
                "site_id": _first_text(group["site_id_text"]),
                "landfill_name": permittee_names[0] if permittee_names else "Landfill",
                "permittee_names": "; ".join(permittee_names),
                "permit_types": ", ".join(permit_types),
                "permit_type_counts": _counted_text(group["PERMIT_TYPE"], type_order=LANDFILL_TYPE_ORDER),
                "permit_actions": _counted_text(group["PERMITTING_ACTION"]),
                "status_group": status_group,
                "status_label": status_label,
                "permit_count": int(len(group)),
                "unique_permit_count": int(unique_permit_count),
                "active_permits": int((group["status_group"] == "active").sum()),
                "pending_permits": int((group["status_group"] == "pending").sum()),
                "permit_numbers": "; ".join(permit_numbers),
                "additional_permit_count": max(unique_permit_count - len(permit_numbers), 0),
                "site_location": _first_text(group["SITE_LOCATION"]),
                "site_city": _first_text(group["SITE_CITY"]),
                "site_zip": _first_text(group["SITE_ZIP"]),
                "county": _first_text(group["COUNTY"]),
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
                "latest_issuance_date": _arcgis_latest_date(group["ISSUANCE_DATE"]),
                "latest_effective_date": _arcgis_latest_date(group["EFFECTIVE_DATE"]),
                "latest_expiration_date": _arcgis_latest_date(group["EXPIRATION_DATE"]),
                "latest_termination_date": _arcgis_latest_date(group["TERMINATION_DATE"]),
                "record_url": _first_text(group["URL"]),
                "geometry": Point(longitude, latitude),
            }
        )

    return gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")


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


def _county_context_frame(
    county_frame: gpd.GeoDataFrame,
    *,
    padding_ratio: float = 0.12,
    min_padding_degrees: float = 0.015,
) -> gpd.GeoDataFrame:
    county_wgs84 = county_frame.to_crs("EPSG:4326")
    minx, miny, maxx, maxy = county_wgs84.total_bounds
    lon_padding = max((maxx - minx) * padding_ratio, min_padding_degrees)
    lat_padding = max((maxy - miny) * padding_ratio, min_padding_degrees)
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


def _clip_to_county_context(
    source: gpd.GeoDataFrame,
    county_frame: gpd.GeoDataFrame,
    *,
    simplify_meters: float,
    keep_columns: list[str],
) -> gpd.GeoDataFrame:
    return _clip_to_frame(
        source,
        _county_context_frame(county_frame),
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
    water_service_areas: gpd.GeoDataFrame,
    service_line_inventory: gpd.GeoDataFrame,
    solid_waste_landfills: gpd.GeoDataFrame,
    protected_areas: gpd.GeoDataFrame,
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

    utility_areas = water_service_areas.copy()
    service_line_lookup = _prepare_service_line_inventory(service_line_inventory)
    utility_areas["PWSID"] = utility_areas["PWSID"].fillna("").astype(str).str.strip().str.upper()
    if not service_line_lookup.empty:
        utility_areas = utility_areas.merge(
            service_line_lookup.rename(columns={"pwsid": "PWSID"}),
            on="PWSID",
            how="left",
        )
    else:
        for output_column in SERVICE_LINE_COUNT_COLUMNS.values():
            utility_areas[output_column] = 0
        utility_areas["service_line_inventory_status"] = "unavailable"
    for output_column in SERVICE_LINE_COUNT_COLUMNS.values():
        utility_areas[output_column] = pd.to_numeric(utility_areas[output_column], errors="coerce").fillna(0).astype(int)
    utility_areas["service_line_inventory_status"] = (
        utility_areas["service_line_inventory_status"].fillna("unavailable").astype(str)
    )
    utility_areas["source_code"] = utility_areas["PL_PSRC"].fillna("").astype(str).str.strip().str.upper()
    utility_areas["source_type"] = utility_areas["source_code"].map(WATER_SOURCE_TYPE_LABELS).fillna("Source type not listed")
    utility_areas["source_group"] = utility_areas["source_code"].map(WATER_SOURCE_GROUPS).fillna("unknown")
    utility_areas["system_name"] = utility_areas["MA_NAME"].fillna("Public water system").astype(str)
    utility_areas["population_served"] = pd.to_numeric(utility_areas["PL_POPL"], errors="coerce").fillna(0).round().astype(int)
    utility_areas["ownership"] = (
        utility_areas["OW_TYPE"].fillna("").astype(str).str.strip().str.upper().map(WATER_OWNERSHIP_LABELS).fillna("")
    )
    utility_areas["dww_link"] = utility_areas["DWW_Link"].fillna("").astype(str)
    utility_areas["geometry"] = utility_areas.geometry.make_valid()
    utility_areas = utility_areas.explode(index_parts=False)
    utility_areas = utility_areas[utility_areas.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    utility_areas = utility_areas.dissolve(
        by=[
            "PWSID",
            "system_name",
            "source_code",
            "source_type",
            "source_group",
            "population_served",
            "ownership",
            "dww_link",
            "total_lines",
            "lead_lines",
            "non_lead_lines",
            "grr_lines",
            "unknown_lines",
            "service_line_inventory_status",
        ],
        as_index=False,
    )
    utility_areas = utility_areas[
        [
            "PWSID",
            "system_name",
            "source_code",
            "source_type",
            "source_group",
            "population_served",
            "ownership",
            "dww_link",
            "total_lines",
            "lead_lines",
            "non_lead_lines",
            "grr_lines",
            "unknown_lines",
            "service_line_inventory_status",
            "geometry",
        ]
    ].rename(columns={"PWSID": "pwsid"})

    protected = protected_areas.copy()
    protected["category"] = protected["Category"].fillna("Unknown").astype(str).str.strip()
    protected["category_group"] = protected["category"].map(PADUS_CATEGORY_GROUPS).fillna("other")
    protected["feature_class"] = protected["FeatClass"].fillna("").astype(str).str.strip()
    protected["unit_name"] = protected["Unit_Nm"].fillna("").astype(str).str.strip()
    protected["local_name"] = protected["Loc_Nm"].fillna("").astype(str).str.strip()
    protected["designation_type"] = protected["Des_Tp"].fillna(protected["Loc_Ds"]).fillna("").astype(str).str.strip()
    protected["owner_type"] = protected["Own_Type"].fillna("").astype(str).str.strip().str.upper()
    protected["owner_type_label"] = protected["owner_type"].map(PADUS_OWNER_TYPE_LABELS).fillna("Unknown")
    protected["owner_name"] = protected["Own_Name"].fillna(protected["Loc_Own"]).fillna("").astype(str).str.strip()
    protected["manager_type"] = protected["Mang_Type"].fillna("").astype(str).str.strip().str.upper()
    protected["manager_type_label"] = protected["manager_type"].map(PADUS_OWNER_TYPE_LABELS).fillna("Unknown")
    protected["manager_name"] = protected["Mang_Name"].fillna(protected["Loc_Mang"]).fillna("").astype(str).str.strip()
    protected["public_access"] = protected["Pub_Access"].fillna("").astype(str).str.strip().str.upper()
    protected["public_access_label"] = protected["public_access"].map(PADUS_ACCESS_LABELS).fillna("Unknown public access")
    protected["gap_status"] = protected["GAP_Sts"].fillna("").astype(str).str.strip()
    protected["gap_status_label"] = protected["gap_status"].map(PADUS_GAP_STATUS_LABELS).fillna("GAP status not assigned")
    protected["acres"] = pd.to_numeric(protected["GIS_Acres"], errors="coerce").fillna(0).round(1)
    protected["easement_holder"] = protected["EsmtHldr"].fillna("").astype(str).str.strip()
    protected["easement_holder_type"] = protected["EHoldTyp"].fillna("").astype(str).str.strip().str.upper()
    protected["easement_holder_type_label"] = (
        protected["easement_holder_type"].map(PADUS_OWNER_TYPE_LABELS).fillna("")
    )
    protected["source_name"] = protected["GIS_Src"].fillna(protected["Agg_Src"]).fillna("").astype(str).str.strip()
    protected["source_date"] = protected["Src_Date"].fillna("").astype(str).str.strip()
    protected["geometry"] = protected.geometry.make_valid()
    protected = protected.explode(index_parts=False)
    protected = protected[protected.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    protected = protected[
        [
            "OBJECTID",
            "feature_class",
            "category",
            "category_group",
            "unit_name",
            "local_name",
            "designation_type",
            "owner_type_label",
            "owner_name",
            "manager_type_label",
            "manager_name",
            "public_access_label",
            "gap_status",
            "gap_status_label",
            "acres",
            "easement_holder",
            "easement_holder_type_label",
            "source_name",
            "source_date",
            "geometry",
        ]
    ].rename(columns={"OBJECTID": "padus_id"})

    landfill_locations = _prepare_landfill_locations(solid_waste_landfills)

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
        utility_layer = _clip_to_county_viewport(
            utility_areas,
            county_frame,
            simplify_meters=180,
            keep_columns=[
                "pwsid",
                "system_name",
                "source_code",
                "source_type",
                "source_group",
                "population_served",
                "ownership",
                "dww_link",
                "total_lines",
                "lead_lines",
                "non_lead_lines",
                "grr_lines",
                "unknown_lines",
                "service_line_inventory_status",
            ],
        )
        protected_layer = _clip_to_county_context(
            protected,
            county_frame,
            simplify_meters=130,
            keep_columns=[
                "padus_id",
                "feature_class",
                "category",
                "category_group",
                "unit_name",
                "local_name",
                "designation_type",
                "owner_type_label",
                "owner_name",
                "manager_type_label",
                "manager_name",
                "public_access_label",
                "gap_status",
                "gap_status_label",
                "acres",
                "easement_holder",
                "easement_holder_type_label",
                "source_name",
                "source_date",
            ],
        )
        landfill_layer = _clip_to_county_context(
            landfill_locations,
            county_frame,
            simplify_meters=0,
            keep_columns=[
                "landfill_id",
                "site_id",
                "landfill_name",
                "permittee_names",
                "permit_types",
                "permit_type_counts",
                "permit_actions",
                "status_group",
                "status_label",
                "permit_count",
                "unique_permit_count",
                "active_permits",
                "pending_permits",
                "permit_numbers",
                "additional_permit_count",
                "site_location",
                "site_city",
                "site_zip",
                "county",
                "latitude",
                "longitude",
                "latest_issuance_date",
                "latest_effective_date",
                "latest_expiration_date",
                "latest_termination_date",
                "record_url",
            ],
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
            "waterUtilities": _feature_collection(utility_layer),
            "protectedAreas": _feature_collection(protected_layer),
            "landfills": _feature_collection(landfill_layer),
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
                "Drinking water utility service-area overlay",
                "Protected-area and conservation easement overlay",
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
            "dataset": "HUC6 basins",
            "purpose": "Basin-scale watershed background and name labels on the statewide home-page map.",
            "sourceName": "USGS WBD MapServer layer 3",
            "sourceUrl": WBD_HUC6_URL.removesuffix("/query"),
            "refreshFrequency": "Periodic",
            "lastUpdated": build_date,
            "notes": "Prototype filters the official WBD basin layer to hydrologic units whose state list includes Tennessee and labels statewide map polygons by the WBD name field.",
        },
        {
            "dataset": "HUC8 watersheds",
            "purpose": "Watershed context for county pages and overlay controls.",
            "sourceName": "USGS WBD MapServer layer 4",
            "sourceUrl": WBD_HUC8_URL.removesuffix("/query"),
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
            "dataset": "Solid waste landfill permit locations",
            "purpose": "Show TDEC solid waste landfill locations on county maps with permit class, status, site address, and permit record links.",
            "sourceName": "TDEC SWM Permits MapServer layer 0",
            "sourceUrl": TDEC_SOLID_WASTE_PERMITS_URL,
            "refreshFrequency": "Periodic",
            "lastUpdated": build_date,
            "notes": "County maps include only solid waste permit records whose PERMIT_TYPE is CLASS I, CLASS II, CLASS III, CLASS IV, or COAL ASH. Convenience centers, recycling centers, transfer stations, tire storage, processing, land application, and special waste records are excluded. Multiple permit records at the same site are aggregated into one landfill point and clipped to a padded county context viewport.",
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
            "purpose": "Show overlapping public drinking water utility service areas, system names, and primary source-water type on county maps.",
            "sourceName": "TDEC TN Public Water System Service Area Boundaries",
            "sourceUrl": TDEC_WATER_SERVICE_AREAS_URL,
            "refreshFrequency": "Periodic",
            "lastUpdated": build_date,
            "notes": f"County summaries and map overlays use the local Harpeth Conservancy snapshot at {WATER_SERVICE_AREAS_PATH}. Polygons are clipped to a padded county viewport for map context and include PWSID, system name, population served, Drinking Water Watch link, and the PL_PSRC primary source-water type code.",
        },
        {
            "dataset": "Lead service line inventory",
            "purpose": "Add service-line inventory counts to drinking water utility map popups.",
            "sourceName": "TDEC Service_Line_Inventory_PWS_Service_Area",
            "sourceUrl": TDEC_SERVICE_LINE_INVENTORY_URL,
            "refreshFrequency": "Periodic",
            "lastUpdated": build_date,
            "notes": "County map overlays join TDEC service-line inventory values to public water system service area polygons by PWSID. Popups include Total Lines, Lead Lines, Non-Lead Lines, GRR, and Unknown Lines.",
        },
        {
            "dataset": "Protected areas and conservation easements",
            "purpose": "Show public protected lands, private and public conservation easements, designations, and related protected-area boundaries on county maps.",
            "sourceName": "USGS PAD-US Protection Mechanism Category",
            "sourceUrl": PADUS_PROTECTION_MECHANISM_URL,
            "refreshFrequency": "PAD-US release cycle",
            "lastUpdated": build_date,
            "notes": "County map overlays use the Tennessee subset of the USGS PAD-US combined inventory, cached as raw GeoJSON during the local data build and clipped to the padded county viewport. Features include the PAD-US protection mechanism category, owner and manager labels, public access, GAP status, acres, easement holder, source name, and source date where available.",
        },
    ]
    (METADATA_DIR / "data-sources.json").write_text(json.dumps(sources, indent=2), encoding="utf8")

    last_updated = {
        "county-pages": build_date,
        "acs": build_date,
        "justice40": build_date,
        "impairment-2026": build_date,
        "epa-attains": build_date,
        "huc6-basins": build_date,
        "watersheds": build_date,
        "districts": build_date,
        "monitoring": build_date,
        "tdec-dwr-public-permits": build_date,
        "tdec-solid-waste-landfills": build_date,
        "epa-echo-cwa": build_date,
        "permits": build_date,
        "tnmap-locator": build_date,
        "scenic-rivers": build_date,
        "water-service-areas": build_date,
        "service-line-inventory": build_date,
        "protected-areas": build_date,
    }
    (METADATA_DIR / "last-updated.json").write_text(json.dumps(last_updated, indent=2), encoding="utf8")
