from __future__ import annotations

import argparse
import json
import math
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests

from scripts.common.prototype_config import COUNTIES_DIR, METADATA_DIR, PUBLIC_DATA

WEEKLY_DIR = PUBLIC_DATA / "weekly"
TDEC_PERMITS_URL = "https://tdeconline.tn.gov/arcgis/rest/services/DWR_Public/MapServer/1/query"
ECHO_CWA_SERVICES_URL = "https://echodata.epa.gov/echo/cwa_rest_services"
ECHO_RESPONSE_SET = 1000
ECHO_QUERY_COLUMNS = ",".join(
    str(column)
    for column in [
        1,  # CWPName
        2,  # SourceID
        9,  # RegistryID
        24,  # FacLat
        25,  # FacLong
        46,  # PermitName
        98,  # CWPSNCStatus
        99,  # CWPVioStatus
        100,  # CWPSNCStatusDate
        101,  # CWPQtrsWithNC
        102,  # CWPViolStatus
        103,  # CWPQtrsWithSNC
        192,  # CWPSNCEventDesc
        195,  # CWP13qtrsComplHistory
        204,  # ViolFlag
        205,  # CurrVioFlag
        215,  # EffExceeds
        230,  # VioLastYear
    ]
)

FeatureCollection = dict[str, Any]
Feature = dict[str, Any]
Properties = dict[str, Any]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf8")
    temporary.replace(path)


def empty_collection() -> FeatureCollection:
    return {"type": "FeatureCollection", "features": []}


def request_json(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, str],
    timeout: int = 120,
    attempts: int = 3,
) -> Any:
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            response = session.get(url, params=params, timeout=timeout)
            if response.status_code == 429:
                response.raise_for_status()
            if response.status_code in {500, 502, 503, 504} and attempt < attempts - 1:
                time.sleep(2 * (attempt + 1))
                continue
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(2 * (attempt + 1))

    raise RuntimeError(f"Request failed for {url}: {last_error}") from last_error


def escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def property_text(properties: Properties | None, key: str) -> str:
    if not properties:
        return ""
    value = properties.get(key)
    return "" if value is None else str(value).strip()


def property_number(properties: Properties | None, key: str) -> float:
    if not properties:
        return 0
    value = properties.get(key)
    if isinstance(value, int | float) and math.isfinite(value):
        return float(value)

    try:
        parsed = float(str(value or "").replace(",", ""))
    except ValueError:
        return 0
    return parsed if math.isfinite(parsed) else 0


def flag_is_yes(value: Any) -> bool:
    if isinstance(value, int | float):
        return value > 0
    return str(value or "").strip().lower() in {"1", "y", "yes", "true"}


def compliance_history(properties: Properties | None) -> str:
    return "".join(property_text(properties, "CWP13qtrsComplHistory").split())


def count_compliance_violations(history: str) -> int:
    return sum(1 for marker in history if marker in {"V", "S"})


def echo_violation_count(properties: Properties | None) -> float:
    reported_quarters = property_number(properties, "CWPQtrsWithNC")
    if reported_quarters > 0:
        return reported_quarters

    history_count = count_compliance_violations(compliance_history(properties))
    if history_count > 0:
        return float(history_count)

    return property_number(properties, "EffExceeds")


def echo_current_violation(properties: Properties | None) -> bool:
    status = property_text(properties, "CWPViolStatus").lower()
    cwp_status = property_text(properties, "CWPStatus").lower()
    return (
        flag_is_yes(properties.get("CurrVioFlag") if properties else None)
        or status == "yes"
        or (len(cwp_status) > 0 and "no violation" not in cwp_status)
    )


def echo_significant_violation(properties: Properties | None) -> bool:
    status = f"{property_text(properties, 'CWPStatus')} {property_text(properties, 'CWPSNCStatus')}".lower()
    return (
        flag_is_yes(properties.get("CurrSvFlag") if properties else None)
        or "significant" in status
        or "snc" in status
    )


def echo_latest_violation_label(properties: Properties | None) -> str:
    current_status = property_text(properties, "CWPStatus")
    current_violation_status = property_text(properties, "CWPViolStatus")
    snc_event = property_text(properties, "CWPSNCEventDesc")
    snc_date = property_text(properties, "CWPSNCStatusDate")

    if echo_current_violation(properties):
        if snc_event and snc_date:
            return f"{snc_event} ({snc_date})"
        if snc_event:
            return snc_event
        if current_status and "no violation" not in current_status.lower():
            return current_status
        if current_violation_status and current_violation_status.lower() != "no":
            return current_violation_status
        return "Current violation flagged by ECHO"

    history = compliance_history(properties)
    for index in range(len(history) - 1, -1, -1):
        marker = history[index]
        if marker not in {"V", "S"}:
            continue

        quarters_ago = len(history) - index - 1
        kind = "Significant noncompliance" if marker == "S" else "Violation"
        if quarters_ago == 0:
            return f"{kind} in the most recent ECHO quarter"
        if quarters_ago == 1:
            return f"{kind} 1 quarter ago"
        return f"{kind} {quarters_ago} quarters ago"

    if flag_is_yes(properties.get("VioLastYear") if properties else None):
        return "Violation in the last 4 quarters"
    if flag_is_yes(properties.get("ViolFlag") if properties else None):
        return "Violation within the last 3 years"

    return "Violation history reported by ECHO"


def echo_detail_url(properties: Properties | None) -> str:
    registry_id = property_text(properties, "RegistryID")
    if registry_id:
        return f"https://echo.epa.gov/detailed-facility-report?fid={registry_id}"

    source_id = property_text(properties, "SourceID")
    return f"https://echo.epa.gov/facilities/facility-search/results?search=permit&keyword={source_id}" if source_id else ""


def echo_feature_display_name(properties: Properties | None) -> str:
    return property_text(properties, "CWPName") or property_text(properties, "PermitName") or "ECHO permit"


def point_coordinates(feature: Feature) -> tuple[float, float] | None:
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return None

    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None

    lon = coordinates[0]
    lat = coordinates[1]
    if isinstance(lon, int | float) and isinstance(lat, int | float):
        return float(lon), float(lat)
    return None


def normalize_echo_feature(feature: Feature) -> Feature:
    properties = dict(feature.get("properties") or {})
    violation_count = echo_violation_count(properties)
    current_violation = echo_current_violation(properties)
    significant_violation = echo_significant_violation(properties)
    source_id = property_text(properties, "SourceID")

    return {
        **feature,
        "properties": {
            **properties,
            "echo_source_id": source_id,
            "echo_display_name": echo_feature_display_name(properties),
            "echo_violation_count": violation_count,
            "echo_current_violation": current_violation,
            "echo_significant_violation": significant_violation,
            "echo_latest_violation": echo_latest_violation_label(properties),
            "echo_detail_url": echo_detail_url(properties),
            "echo_status_label": "Current violation" if current_violation else "Recent violation",
        },
    }


def normalize_echo_collection(collection: FeatureCollection) -> FeatureCollection:
    features = [
        feature
        for feature in (normalize_echo_feature(item) for item in collection.get("features", []))
        if point_coordinates(feature) and property_number(feature.get("properties"), "echo_violation_count") > 0
    ]
    return {"type": "FeatureCollection", "features": features}


def echo_results(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    results = payload.get("Results")
    return results if isinstance(results, dict) else None


def echo_error_message(payload: Any) -> str:
    results = echo_results(payload)
    error = results.get("Error") if results else None
    if not isinstance(error, dict):
        return ""
    message = error.get("ErrorMessage")
    return message if isinstance(message, str) else ""


def echo_query_id(payload: Any) -> str:
    query_id = (echo_results(payload) or {}).get("QueryID")
    return str(query_id) if query_id is not None else ""


def echo_query_rows(payload: Any) -> int:
    query_rows = (echo_results(payload) or {}).get("QueryRows")
    try:
        return int(str(query_rows or "0"))
    except ValueError:
        return 0


def facilities_to_feature_collection(payload: Any) -> FeatureCollection:
    root = payload if isinstance(payload, dict) else {}
    results = root.get("Results") if isinstance(root.get("Results"), dict) else {}
    facilities = results.get("Facilities") or root.get("Facilities") or []
    features: list[Feature] = []

    for facility in facilities if isinstance(facilities, list) else []:
        if not isinstance(facility, dict):
            continue
        try:
            lon = float(str(facility.get("FacLong") or ""))
            lat = float(str(facility.get("FacLat") or ""))
        except ValueError:
            continue
        if not math.isfinite(lon) or not math.isfinite(lat):
            continue
        features.append(
            {
                "type": "Feature",
                "properties": facility,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            }
        )

    return {"type": "FeatureCollection", "features": features}


def echo_facility_collection(payload: Any) -> FeatureCollection:
    if isinstance(payload, dict) and payload.get("type") == "FeatureCollection" and isinstance(payload.get("features"), list):
        return payload
    return facilities_to_feature_collection(payload)


def fetch_echo_violations(session: requests.Session, county_name: str) -> FeatureCollection:
    query_payload = request_json(
        session,
        f"{ECHO_CWA_SERVICES_URL}.get_facilities",
        params={
            "output": "JSON",
            "p_st": "TN",
            "p_co": county_name,
            "p_act": "Y",
            "responseset": str(ECHO_RESPONSE_SET),
        },
    )
    query_error = echo_error_message(query_payload)
    if query_error:
        raise RuntimeError(f"ECHO query failed for {county_name}: {query_error}")

    query_id = echo_query_id(query_payload)
    if not query_id:
        return normalize_echo_collection(echo_facility_collection(query_payload))

    pages = max(1, math.ceil(echo_query_rows(query_payload) / ECHO_RESPONSE_SET))
    features: list[Feature] = []
    for page in range(1, pages + 1):
        page_payload = request_json(
            session,
            f"{ECHO_CWA_SERVICES_URL}.get_qid",
            params={
                "output": "JSON",
                "qid": query_id,
                "pageno": str(page),
                "responseset": str(ECHO_RESPONSE_SET),
                "qcolumns": ECHO_QUERY_COLUMNS,
            },
        )
        page_error = echo_error_message(page_payload)
        if page_error:
            raise RuntimeError(f"ECHO page request failed for {county_name}: {page_error}")

        page_features = echo_facility_collection(page_payload).get("features", [])
        features.extend(page_features)
        if len(page_features) < ECHO_RESPONSE_SET:
            break

    return normalize_echo_collection({"type": "FeatureCollection", "features": features})


def fetch_paged_geojson(
    session: requests.Session,
    url: str,
    base_params: dict[str, str],
    *,
    page_size: int = 1000,
    max_pages: int = 12,
) -> FeatureCollection:
    features: list[Feature] = []

    for page in range(max_pages):
        params = {
            **base_params,
            "resultOffset": str(page * page_size),
            "resultRecordCount": str(page_size),
        }
        payload = request_json(session, url, params=params)
        page_features = payload.get("features", []) if isinstance(payload, dict) else []
        features.extend(page_features)

        exceeded_limit = bool(payload.get("exceededTransferLimit")) if isinstance(payload, dict) else False
        if len(page_features) < page_size or not exceeded_limit:
            break

    return {"type": "FeatureCollection", "features": features}


def permit_status(properties: Properties) -> str:
    return "Active" if str(properties.get("PERMITTING_ACTION") or "") == "Active" else "Pending"


def fetch_tdec_permits(session: requests.Session, county_name: str) -> FeatureCollection:
    county = escape_sql_literal(county_name)
    collection = fetch_paged_geojson(
        session,
        TDEC_PERMITS_URL,
        {
            "where": f"COUNTY = '{county}' AND PERMITTING_ACTION IN ('Active','Pending','Incomplete')",
            "outFields": (
                "PERMIT_NUMBER,PERMITTEE_NAME,PERMITTING_ACTION,PERMIT_TYPE,ISSUANCE_DATE,"
                "EFFECTIVE_DATE,EXPIRATION_DATE,TERMINATION_DATE,COUNTY,SITE_LOCATION,URL,"
                "LATITUDE,LONGITUDE"
            ),
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
    )
    features = []
    for feature in collection.get("features", []):
        properties = dict(feature.get("properties") or {})
        features.append(
            {
                **feature,
                "properties": {
                    **properties,
                    "permit_status": permit_status(properties),
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


def load_counties(filters: list[str]) -> list[dict[str, Any]]:
    counties = read_json(COUNTIES_DIR / "index.json")
    if not filters:
        return counties

    wanted = {item.lower() for item in filters}
    selected = [
        county
        for county in counties
        if str(county.get("slug", "")).lower() in wanted or str(county.get("name", "")).lower() in wanted
    ]
    found = {str(county.get("slug", "")).lower() for county in selected} | {
        str(county.get("name", "")).lower() for county in selected
    }
    missing = sorted(wanted - found)
    if missing:
        raise SystemExit(f"Unknown county filter(s): {', '.join(missing)}")
    return selected


def refresh_county(session: requests.Session, county: dict[str, Any]) -> dict[str, Any]:
    slug = str(county["slug"])
    name = str(county["name"])
    county_dir = WEEKLY_DIR / slug
    result = {
        "slug": slug,
        "name": name,
        "tdec": {"status": "skipped", "features": 0},
        "echo": {"status": "skipped", "features": 0},
    }

    try:
        permits = fetch_tdec_permits(session, name)
        write_json(county_dir / "tdec-permits.geojson", permits)
        result["tdec"] = {"status": "ok", "features": len(permits.get("features", []))}
    except Exception as exc:  # noqa: BLE001 - keep weekly deploys best-effort by default.
        result["tdec"] = {"status": "error", "features": 0, "message": str(exc)}

    try:
        echo = fetch_echo_violations(session, name)
        write_json(county_dir / "echo-violations.geojson", echo)
        result["echo"] = {"status": "ok", "features": len(echo.get("features", []))}
    except Exception as exc:  # noqa: BLE001 - keep weekly deploys best-effort by default.
        result["echo"] = {"status": "error", "features": 0, "message": str(exc)}

    return result


def update_source_metadata(refresh_date: str, results: list[dict[str, Any]]) -> None:
    tdec_ok = any(result["tdec"]["status"] == "ok" for result in results)
    echo_ok = any(result["echo"]["status"] == "ok" for result in results)

    last_updated_path = METADATA_DIR / "last-updated.json"
    if last_updated_path.exists():
        last_updated = read_json(last_updated_path)
        if tdec_ok:
            last_updated["tdec-dwr-public-permits"] = refresh_date
        if echo_ok:
            last_updated["epa-echo-cwa"] = refresh_date
        write_json(last_updated_path, last_updated)

    sources_path = METADATA_DIR / "data-sources.json"
    if sources_path.exists():
        sources = read_json(sources_path)
        for source in sources:
            if source.get("dataset") == "TDEC DWR public water resources permits" and tdec_ok:
                source["refreshFrequency"] = "Weekly cache"
                source["lastUpdated"] = refresh_date
                source["notes"] = (
                    "County maps use a static weekly cache generated from the public TDEC DWR MapServer. "
                    "The browser falls back to the live service when a cache file is unavailable."
                )
            if source.get("dataset") == "EPA ECHO CWA permit compliance" and echo_ok:
                source["refreshFrequency"] = "Weekly cache"
                source["lastUpdated"] = refresh_date
                source["notes"] = (
                    "County maps use a static weekly cache generated from EPA ECHO CWA REST Services. "
                    "Records include recent or current noncompliance signals and links to ECHO reports."
                )
        write_json(sources_path, sources)


def write_manifest(refresh_date: str, results: list[dict[str, Any]]) -> None:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    write_json(
        WEEKLY_DIR / "manifest.json",
        {
            "generatedAt": generated_at,
            "refreshDate": refresh_date,
            "sources": {
                "tdec": {
                    "dataset": "TDEC DWR public water resources permits",
                    "url": TDEC_PERMITS_URL,
                },
                "echo": {
                    "dataset": "EPA ECHO CWA permit compliance",
                    "url": f"{ECHO_CWA_SERVICES_URL}.get_facilities",
                },
            },
            "counties": results,
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh weekly EPA ECHO and TDEC permit static caches.")
    parser.add_argument(
        "--county",
        action="append",
        default=[],
        help="Limit refresh to one county slug or county name. Repeat for multiple counties.",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Refresh date written to source metadata during a full refresh.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any county/source refresh fails.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    counties = load_counties(args.county)
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://tdeconline.tn.gov",
            "Referer": "https://tdeconline.tn.gov/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36 PolicyWatch/0.1"
            ),
        }
    )

    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for index, county in enumerate(counties, start=1):
        name = str(county["name"])
        slug = str(county["slug"])
        print(f"[{index}/{len(counties)}] Refreshing {name} County ({slug})")
        result = refresh_county(session, county)
        results.append(result)
        print(
            "  TDEC: {tdec_status} ({tdec_count}); ECHO: {echo_status} ({echo_count})".format(
                tdec_status=result["tdec"]["status"],
                tdec_count=result["tdec"]["features"],
                echo_status=result["echo"]["status"],
                echo_count=result["echo"]["features"],
            )
        )

    write_manifest(args.date, results)
    if not args.county:
        update_source_metadata(args.date, results)

    failures = [
        f"{result['slug']}:{source}"
        for result in results
        for source in ["tdec", "echo"]
        if result[source]["status"] != "ok"
    ]
    if failures:
        print(f"Weekly refresh completed with {len(failures)} source failure(s): {', '.join(failures[:20])}")
        if args.strict:
            raise SystemExit(1)
    else:
        print("Weekly refresh completed successfully.")


if __name__ == "__main__":
    main()
