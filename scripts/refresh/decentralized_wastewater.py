"""Cache basic TDEC drip-survey locations and attach one point per permit to counties."""
from __future__ import annotations

import argparse
import copy
import math
import re
from collections import defaultdict
from datetime import date, datetime, timezone

import requests
from shapely.geometry import shape

from scripts.common.prototype_config import COUNTY_MAPS_DIR, LAYERS_DIR, METADATA_DIR
from scripts.common.source_archive import archived_refresh, archive_json
from scripts.refresh.weekly_layers import fetch_paged_geojson, read_json, request_json, write_json, TDEC_PERMITS_URL

DATASET = "Decentralized wastewater systems"
DETAIL_DATASET = "Decentralized wastewater permit details"
DASHBOARD_URL = "https://www.arcgis.com/apps/dashboards/c83fa34306ce4283b6cdec1f8e35259a"
SOURCE_URL = ("https://services5.arcgis.com/bPacKTm9cauMXVfn/arcgis/rest/services/"
              "survey123_dce334d35bf84db4a7293ed70dd078e0/FeatureServer/0")
WHERE = "untitled_question_67_other NOT LIKE '%Remove%'"
CACHE_PATH = LAYERS_DIR / "decentralized-wastewater.geojson"
DETAIL_PATH = LAYERS_DIR / "decentralized-wastewater-permits.json"
SURVEY_FIELDS = (
    "objectid", "sop_tracking_number", "SOP_Other", "date_of_site_visit", "EditDate",
    "this_system_is_serving_select_a", "field_63_other", "th_system_is_serving_other",
)
PERMIT_FIELDS = (
    "PERMIT_NUMBER", "PERMITTEE_NAME", "PERMITTING_ACTION", "PERMIT_TYPE", "COUNTY",
    "SITE_LOCATION", "ISSUANCE_DATE", "EFFECTIVE_DATE", "EXPIRATION_DATE", "URL",
)


def permit_number(value: str) -> str:
    match = re.search(r"\b(?:SOP[\s-]*(\d{5})|(TN\d{7}))\b", value, re.I)
    if not match:
        raise ValueError(f"Unrecognized survey permit number: {value!r}")
    return "SOP-" + match[1] if match[1] else match[2].upper()


def iso_date(value) -> str:
    return datetime.fromtimestamp(float(value) / 1000, timezone.utc).date().isoformat() if value else ""


def normalize_survey(payload: dict, definition: dict, details: dict) -> dict:
    fields = {field["name"]: field for field in definition.get("fields", [])}
    if set(SURVEY_FIELDS) - fields.keys():
        raise ValueError("The TDEC survey schema changed; required basic fields are missing")
    labels = {str(item["code"]): item["name"] for item in
              (fields["sop_tracking_number"].get("domain") or {}).get("codedValues", [])}
    grouped = defaultdict(list)
    seen = set()
    for feature in payload["features"]:
        p = feature.get("properties") or {}
        oid = p.get("objectid")
        coordinates = (feature.get("geometry") or {}).get("coordinates", [])
        if (oid is None or oid in seen or feature.get("geometry", {}).get("type") != "Point"
                or len(coordinates) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in coordinates)
                or not (-180 <= coordinates[0] <= 180 and -90 <= coordinates[1] <= 90)):
            raise ValueError("Invalid or duplicate TDEC survey point; previous layer retained")
        seen.add(oid)
        label = labels.get(str(p.get("sop_tracking_number")), p.get("sop_tracking_number") or "")
        if label.lower() == "other":
            label = p.get("SOP_Other") or ""
        grouped[permit_number(label)].append((feature, label))
    if not grouped:
        raise ValueError("Unexpected empty TDEC drip survey; previous layer retained")
    features = []
    for number, records in sorted(grouped.items()):
        feature, label = max(records, key=lambda item: (
            item[0]["properties"].get("date_of_site_visit") or 0,
            item[0]["properties"].get("EditDate") or 0, item[0]["properties"]["objectid"],
        ))
        p = feature["properties"]
        permit = details.get("permits", {}).get(number, {})
        name = re.sub(r"^\s*(?:SOP[\s-]*\d{5}|TN\d{7})\s*[-:]?\s*", "", label, flags=re.I).strip()
        serves = str(p.get("this_system_is_serving_select_a") or "").replace(",", ", ")
        serves = re.sub(r"\bother\b", lambda _: p.get("field_63_other") or p.get("th_system_is_serving_other") or "Other", serves, flags=re.I)
        features.append({"type": "Feature", "id": number, "geometry": copy.deepcopy(feature["geometry"]), "properties": {
            "system_id": number, "permit_number": number, "system_name": name or number,
            "permittee": permit.get("PERMITTEE_NAME") or "",
            "permit_action": permit.get("PERMITTING_ACTION") or "",
            "address": permit.get("SITE_LOCATION") or "",
            "permit_details_date": details.get("retrievedAt", "") if permit else "",
            "survey_date": iso_date(p.get("date_of_site_visit")), "survey_count": len(records),
            "serves": serves, "expires": iso_date(permit.get("EXPIRATION_DATE")),
        }})
    return {"type": "FeatureCollection", "features": features,
            "sourceUrl": SOURCE_URL, "dashboardUrl": DASHBOARD_URL,
            "retrievedAt": date.today().isoformat(), "surveyRecords": len(seen),
            "sourceLastEditedAt": iso_date(definition.get("editingInfo", {}).get("dataLastEditDate"))}


def county_payloads(payload: dict) -> list[tuple]:
    counties = []
    for path in sorted(COUNTY_MAPS_DIR.glob("*.json")):
        county = read_json(path)
        geometries = [shape(f["geometry"]) for f in county["county"]["features"]]
        counties.append((path, county, geometries))
    assigned = defaultdict(list)
    for feature in payload["features"]:
        point = shape(feature["geometry"])
        matches = [county["slug"] for _, county, geometries in counties if any(g.covers(point) for g in geometries)]
        if len(matches) != 1:
            raise ValueError(f"Survey location {feature['id']} cannot be uniquely assigned to a county")
        output = copy.deepcopy(feature)
        output["properties"]["county_slug"] = matches[0]
        assigned[matches[0]].append(output)
    for _, county, _ in counties:
        county["decentralizedWastewater"] = {"type": "FeatureCollection", "features": assigned[county["slug"]]}
        county["decentralizedWastewaterUpdatedAt"] = payload["retrievedAt"]
    return [(path, county) for path, county, _ in counties]


def register_sources(payload: dict, details: dict) -> None:
    path = METADATA_DIR / "data-sources.json"
    sources = [s for s in read_json(path) if s["dataset"] not in {DATASET, DETAIL_DATASET}]
    sources.extend([
        {"dataset": DATASET, "purpose": "Locate decentralized wastewater systems surveyed by TDEC.",
         "sourceName": "TDEC Division of Water Resources — SOP Drip Investigation Survey",
         "sourceUrl": DASHBOARD_URL, "lastUpdated": payload["retrievedAt"], "lastChecked": payload["retrievedAt"],
         "refreshFrequency": "Weekly check; latest available agency release", "refreshStatus": "Current",
         "notes": "One marker per SOP or TN permit at its latest surveyed location; repeat visits are grouped. "
                  "Full system names use the survey's coded-value labels. The dashboard's removal filter is preserved. "
                  "Survey points may locate drip fields rather than treatment buildings and do not establish current operating status. "
                  "This survey is not a complete statewide plant inventory. No photos, attachments, inspector names, or inspection narratives are downloaded. "
                  f"Agency data last edited: {payload.get('sourceLastEditedAt') or 'not supplied'}."},
        {"dataset": DETAIL_DATASET, "purpose": "Identify listed permittees and basic permit information for surveyed systems.",
         "sourceName": "TDEC DWR public water resources permits", "sourceUrl": TDEC_PERMITS_URL,
         "lastUpdated": details.get("retrievedAt", ""), "lastChecked": details.get("lastChecked", ""),
         "refreshFrequency": "Weekly check; latest available agency release",
         "refreshStatus": details.get("refreshStatus", "Not available"),
         "notes": "Joined by exact normalized SOP/TN permit number, across all permit actions. Permittee is the agency's listed entity, "
                  "not independently verified legal ownership. Unmatched systems retain their survey names with no inferred owner. "
                  "When TDEC rejects access, earlier permit details and their retrieval dates are retained independently of survey updates."},
    ])
    write_json(path, sources)
    dates_path = METADATA_DIR / "last-updated.json"
    dates = read_json(dates_path)
    dates["decentralized-wastewater"] = payload["retrievedAt"]
    if details.get("retrievedAt"):
        dates["decentralized-wastewater-permits"] = details["retrievedAt"]
    write_json(dates_path, dates)


def apply_cached() -> None:
    payload = read_json(CACHE_PATH)
    outputs = county_payloads(payload)  # Validate every assignment before writing any county.
    for path, county in outputs:
        write_json(path, county, compact=True)
    register_sources(payload, read_json(DETAIL_PATH))
    print(f"Attached {len(payload['features'])} decentralized wastewater systems to county maps.", flush=True)


@archived_refresh("Decentralized wastewater refresh")
def refresh() -> list[str]:
    errors = []
    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0 PolicyWatch public data refresh"})
        source_definition = request_json(session, SOURCE_URL, params={"f": "json"})
        definition = {"name": source_definition.get("name"), "editingInfo": source_definition.get("editingInfo", {}),
                      "fields": [field for field in source_definition.get("fields", []) if field["name"] in SURVEY_FIELDS]}
        archive_json("TDEC drip-survey field definitions", definition, url=SOURCE_URL, kind="service-definition")
        count = request_json(session, SOURCE_URL + "/query", params={"f": "json", "where": WHERE, "returnCountOnly": "true"})
        survey = fetch_paged_geojson(session, SOURCE_URL + "/query", {
            "where": WHERE, "outFields": ",".join(SURVEY_FIELDS), "outSR": "4326",
            "returnGeometry": "true", "f": "geojson", "orderByFields": "objectid",
        }, max_pages=100)
        if type(count.get("count")) is not int or len(survey["features"]) != count["count"]:
            raise ValueError("Incomplete TDEC drip-survey download; previous layer retained")
        details = read_json(DETAIL_PATH) if DETAIL_PATH.exists() else {"permits": {}}
        preliminary = normalize_survey(survey, definition, details)
        numbers = [f["properties"]["permit_number"] for f in preliminary["features"]]
        try:
            permits = {}
            for offset in range(0, len(numbers), 75):
                where = "PERMIT_NUMBER IN (" + ",".join("'" + number + "'" for number in numbers[offset:offset + 75]) + ")"
                data = fetch_paged_geojson(session, TDEC_PERMITS_URL, {
                    "where": where, "outFields": ",".join(PERMIT_FIELDS), "returnGeometry": "false",
                    "f": "geojson", "orderByFields": "OBJECTID",
                }, max_pages=100)
                for feature in data["features"]:
                    p = feature["properties"]
                    if set(PERMIT_FIELDS) - p.keys() or p["PERMIT_NUMBER"] not in numbers:
                        raise ValueError("Unexpected TDEC permit detail response")
                    if p["PERMIT_NUMBER"] in permits:
                        raise ValueError("Duplicate TDEC permit number; details retained for review")
                    permits[p["PERMIT_NUMBER"]] = p
            if not permits:
                raise ValueError("Unexpected empty TDEC permit detail response")
            details = {"permits": permits, "retrievedAt": date.today().isoformat(), "refreshStatus": "Current"}
        except Exception as exc:
            errors.append(f"{DETAIL_DATASET}: {exc}")
            details["refreshStatus"] = "Refresh failed; previous data retained"
            print(f"::warning::{errors[-1]}", flush=True)
        details["lastChecked"] = date.today().isoformat()
        payload = normalize_survey(survey, definition, details)
        county_payloads(payload)
        write_json(DETAIL_PATH, details)
        write_json(CACHE_PATH, payload)
        apply_cached()
    return errors


@archived_refresh("Decentralized wastewater command")
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached", action="store_true")
    args = parser.parse_args()
    from scripts.refresh.online_sources import transaction
    if args.cached:
        transaction(apply_cached)
    else:
        transaction(refresh)


if __name__ == "__main__":
    main()
