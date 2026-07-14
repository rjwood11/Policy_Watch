from __future__ import annotations

import json

from scripts.common.prototype_config import COUNTIES_DIR, COUNTY_MAPS_DIR, METADATA_DIR, SEARCH_DIR


def _read_json(path):
    return json.loads(path.read_text(encoding="utf8"))


def validate_outputs() -> list[str]:
    errors: list[str] = []

    county_index = _read_json(COUNTIES_DIR / "index.json")
    if not county_index:
        errors.append("County index is empty.")

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
            if "watersheds" not in county_map_payload:
                errors.append(f"{county_map_path.name} is missing 'watersheds'.")

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
