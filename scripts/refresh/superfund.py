"""Cache EPA's official Superfund point layer and attach sites to county maps."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen

from scripts.common.prototype_config import COUNTY_MAPS_DIR, LAYERS_DIR, METADATA_DIR

SOURCE_URL = (
    "https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/"
    "Superfund_National_Priorities_List_(NPL)_Sites_with_Status_Information/FeatureServer/0"
)
CACHE_PATH = LAYERS_DIR / "superfund-sites.geojson"
FIELDS = "Site_Name,Site_EPA_ID,State,City,County,Status,Site_Progress_Profile,Listing_Date,Deletion_Date"


def refresh_cache() -> dict:
    params = urlencode({
        "where": "State = 'Tennessee'", "outFields": FIELDS,
        "outSR": 4326, "f": "geojson", "resultRecordCount": 2000,
    })
    with urlopen(f"{SOURCE_URL}/query?{params}", timeout=60) as response:
        payload = json.load(response)
    if payload.get("type") != "FeatureCollection" or not payload.get("features"):
        raise ValueError(f"EPA returned an invalid or empty Superfund response: {payload}")
    if payload.get("exceededTransferLimit") or payload.get("properties", {}).get("exceededTransferLimit"):
        raise ValueError("EPA Superfund response exceeded the transfer limit; cache was preserved.")
    seen = set()
    for feature in payload["features"]:
        properties = feature["properties"]
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point" or len(geometry.get("coordinates", [])) != 2:
            raise ValueError(f"Missing point geometry for {properties.get('Site_Name')}")
        site_id = properties.get("Site_EPA_ID")
        if not site_id or site_id in seen or not properties.get("County"):
            raise ValueError(f"Missing or duplicate site ID / county: {properties}")
        seen.add(site_id)
        # The service publishes HTML anchors; retain only the trusted EPA URL.
        match = re.search(r'href=[\"\']([^\"\']+)', properties.pop("Site_Progress_Profile", "") or "")
        url = match.group(1) if match else ""
        parsed = urlparse(url)
        properties["profile_url"] = url if parsed.scheme == "https" and parsed.hostname == "cumulis.epa.gov" else ""
    payload.pop("crs", None)
    payload["sourceUrl"] = SOURCE_URL
    payload["retrievedAt"] = date.today().isoformat()
    CACHE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf8")
    return payload


def apply_cached_superfund() -> None:
    payload = json.loads(CACHE_PATH.read_text(encoding="utf8"))
    assigned = set()
    relevant_counties = 0
    for path in sorted(COUNTY_MAPS_DIR.glob("*.json")):
        county = json.loads(path.read_text(encoding="utf8"))
        features = [
            feature for feature in payload["features"]
            if county["name"].casefold() in {
                name.strip().casefold() for name in feature["properties"]["County"].split(",")
            }
        ]
        assigned.update(feature["properties"]["Site_EPA_ID"] for feature in features)
        relevant_counties += bool(features)
        county["superfundSites"] = {"type": "FeatureCollection", "features": features}
        county["superfundUpdatedAt"] = payload["retrievedAt"]
        path.write_text(json.dumps(county, separators=(",", ":")), encoding="utf8")
    if len(assigned) != len(payload["features"]):
        raise ValueError("Some EPA Superfund sites could not be assigned to a county.")
    sources_path = METADATA_DIR / "data-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf8"))
    sources = [source for source in sources if source["dataset"] != "Superfund sites"]
    sources.append({
        "dataset": "Superfund sites",
        "purpose": "Locate EPA Superfund sites on county maps with listing status and site profiles.",
        "sourceName": "US EPA Superfund NPL Sites with Status Information",
        "sourceUrl": SOURCE_URL,
        "refreshFrequency": "Manual: npm run data:refresh-superfund",
        "lastUpdated": payload["retrievedAt"],
        "notes": "Point layer used in EPA's official Where You Live map. Includes current and deleted NPL sites; status is retained as published. County assignment follows EPA's County field, including multi-county sites. Markers are reference locations, not site or contamination boundaries. An empty county means no sites in this dataset, not an absence of all contaminated properties.",
    })
    sources_path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf8")
    print(f"Attached {len(assigned)} EPA Superfund sites to {relevant_counties} county maps.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached", action="store_true", help="Apply the committed cache without downloading.")
    args = parser.parse_args()
    if not args.cached:
        refresh_cache()
    apply_cached_superfund()


if __name__ == "__main__":
    main()
