from __future__ import annotations

import json
import struct

from scripts.common.prototype_config import COUNTIES_DIR, COUNTY_MAPS_DIR, METADATA_DIR, SEARCH_DIR

UTILITY_SERVICE_LINE_FIELDS = {
    "total_lines",
    "lead_lines",
    "non_lead_lines",
    "grr_lines",
    "unknown_lines",
    "service_line_inventory_status",
}


def _read_json(path):
    return json.loads(path.read_text(encoding="utf8"))


def validate_outputs() -> list[str]:
    errors: list[str] = []

    county_index = _read_json(COUNTIES_DIR / "index.json")
    if not county_index:
        errors.append("County index is empty.")

    landuse_dir = COUNTY_MAPS_DIR.parent / "landuse"
    manifest_path = landuse_dir / "manifest.json"
    if not manifest_path.exists():
        errors.append("Missing local land-cover manifest.")
    else:
        manifest = _read_json(manifest_path)
        for county in county_index:
            raster = manifest.get("counties", {}).get(county.get("slug"))
            image_path = landuse_dir / f"{county.get('slug')}.png"
            if not raster or not image_path.exists():
                errors.append(f"Missing land-cover image / metadata for {county.get('slug')}.")
                continue
            header = image_path.read_bytes()[:24]
            if header[:8] != b"\x89PNG\r\n\x1a\n" or len(header) < 24:
                errors.append(f"Invalid land-cover PNG for {county.get('slug')}.")
            elif struct.unpack(">II", header[16:24]) != (raster["width"], raster["height"]):
                errors.append(f"Land-cover PNG dimensions disagree for {county.get('slug')}.")

    if not (COUNTY_MAPS_DIR.parent / "layers" / "huc6.geojson").exists():
        errors.append("Missing statewide HUC6 layer.")

    for county in county_index:
        slug = county.get("slug")
        if not slug:
            errors.append("County index contains an entry without a slug.")
            continue

        county_path = COUNTIES_DIR / f"{slug}.json"
        if not county_path.exists():
            errors.append(f"Missing county payload for slug '{slug}'.")
            continue

        payload = _read_json(county_path)
        for key in ["name", "region", "overview", "prototypeStatus", "indicators", "stressSummary", "rankings", "buildDate"]:
            if key not in payload:
                errors.append(f"{county_path.name} is missing '{key}'.")

        for indicator in payload.get("indicators", []):
            if "stateRank" not in indicator:
                errors.append(f"{county_path.name} indicator '{indicator.get('key')}' is missing 'stateRank'.")

        county_map_path = COUNTY_MAPS_DIR / f"{slug}.json"
        if not county_map_path.exists():
            errors.append(f"Missing county map payload for slug '{slug}'.")
        else:
            county_map_payload = _read_json(county_map_path)
            superfund = county_map_payload.get("superfundSites")
            if not isinstance(superfund, dict) or superfund.get("type") != "FeatureCollection":
                errors.append(f"{county_map_path.name} is missing the Superfund collection.")
            else:
                for feature in superfund.get("features", []):
                    properties = feature.get("properties", {})
                    counties = {name.strip().casefold() for name in properties.get("County", "").split(",")}
                    if county_map_payload["name"].casefold() not in counties:
                        errors.append(f"{county_map_path.name} contains a Superfund site assigned to another county.")
                    if feature.get("geometry", {}).get("type") != "Point" or not properties.get("Site_EPA_ID"):
                        errors.append(f"{county_map_path.name} contains an invalid Superfund point.")
            if "watersheds" not in county_map_payload:
                errors.append(f"{county_map_path.name} is missing 'watersheds'.")
            if "waterUtilities" not in county_map_payload:
                errors.append(f"{county_map_path.name} is missing 'waterUtilities'.")
            for feature in county_map_payload.get("waterUtilities", {}).get("features", []):
                properties = feature.get("properties", {})
                missing_fields = UTILITY_SERVICE_LINE_FIELDS - set(properties)
                if missing_fields:
                    errors.append(
                        f"{county_map_path.name} utility '{properties.get('pwsid')}' is missing service-line fields: "
                        f"{', '.join(sorted(missing_fields))}."
                    )
                    break
            if "protectedAreas" not in county_map_payload:
                errors.append(f"{county_map_path.name} is missing 'protectedAreas'.")
            if "landfills" not in county_map_payload:
                errors.append(f"{county_map_path.name} is missing 'landfills'.")

    sources = _read_json(METADATA_DIR / "data-sources.json")
    if not sources:
        errors.append("Source metadata is empty.")

    search_index = _read_json(SEARCH_DIR / "search-index.json")
    if len(search_index) != len(county_index):
        errors.append("Search index count does not match county index count.")

    return errors


def main() -> None:
    errors = validate_outputs()
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
