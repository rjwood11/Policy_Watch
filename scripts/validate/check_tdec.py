"""Read-only access check for the complete TDEC feeds used by the refresh."""
from __future__ import annotations

import requests

from scripts.common.prototype_config import TDEC_SOLID_WASTE_PERMITS_URL
from scripts.refresh.weekly_layers import TDEC_PERMITS_URL, request_json


def main() -> None:
    failures = []
    with requests.Session() as session:
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36 PolicyWatch/0.1"
            ),
            "Origin": "https://tdeconline.tn.gov",
            "Referer": "https://tdeconline.tn.gov/",
        })
        for name, url in [
            ("Water permits", TDEC_PERMITS_URL.removesuffix("/query")),
            ("Landfill permits", TDEC_SOLID_WASTE_PERMITS_URL),
        ]:
            try:
                metadata = request_json(session, url, params={"f": "json"})
                required = {"PERMIT_NUMBER", "PERMITTEE_NAME", "PERMITTING_ACTION",
                            "PERMIT_TYPE", "COUNTY", "ISSUANCE_DATE", "EXPIRATION_DATE"}
                missing = required - {field["name"] for field in metadata.get("fields", [])}
                if missing:
                    raise ValueError(f"Required permit fields are missing: {sorted(missing)}")
                count = request_json(session, url + "/query", params={
                    "f": "json", "where": "1=1", "returnCountOnly": "true",
                }).get("count")
                if type(count) is not int or count <= 0:
                    raise ValueError("Missing or empty statewide permit count")
                sample = request_json(session, url + "/query", params={
                    "f": "geojson", "where": "1=1", "outFields": ",".join(sorted(required)),
                    "returnGeometry": "true", "outSR": "4326", "resultRecordCount": "1",
                })
                if sample.get("type") != "FeatureCollection" or not sample.get("features"):
                    raise ValueError("Permit feature query did not return any GeoJSON records")
                print(f"{name}: accessible; {count} statewide permit records", flush=True)
            except Exception as exc:
                failures.append(name)
                print(f"{name}: FAILED: {exc}", flush=True)
    if failures:
        raise SystemExit("Complete TDEC feed access failed: " + ", ".join(failures))


if __name__ == "__main__":
    main()
