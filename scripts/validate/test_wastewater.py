"""Coverage, deduplication, and source-failure checks for the drip-survey layer."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.refresh import decentralized_wastewater as wastewater
from scripts.refresh import online_sources as online


def fixture():
    definition = {"fields": [{"name": field} for field in wastewater.SURVEY_FIELDS]}
    next(f for f in definition["fields"] if f["name"] == "sop_tracking_number")["domain"] = {
        "codedValues": [{"code": "SOP-11001 - Short", "name": "SOP-11001 - Full system name"}],
    }
    feature = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-86.8, 36.1]},
               "properties": {"objectid": 1, "sop_tracking_number": "SOP-11001 - Short",
                              "date_of_site_visit": 1704067200000, "EditDate": 1704067200000}}
    return definition, {"type": "FeatureCollection", "features": [feature]}


class WastewaterTests(unittest.TestCase):
    def test_repeated_visits_group_by_permit_and_use_latest_survey_location(self):
        definition, payload = fixture()
        later = copy.deepcopy(payload["features"][0])
        later["properties"].update(objectid=2, date_of_site_visit=1735689600000)
        later["geometry"]["coordinates"] = [-86.7, 36.2]
        payload["features"].append(later)
        # A late edit to an earlier visit must not replace the later visit.
        payload["features"][0]["properties"]["EditDate"] = 1767225600000
        result = wastewater.normalize_survey(payload, definition, {"permits": {
            "SOP-11001": {"PERMITTEE_NAME": "Listed utility"}}, "retrievedAt": "2026-01-01"})
        self.assertEqual(len(result["features"]), 1)
        feature = result["features"][0]
        self.assertEqual(feature["geometry"]["coordinates"], [-86.7, 36.2])
        self.assertEqual(feature["properties"]["survey_count"], 2)
        self.assertEqual(feature["properties"]["system_name"], "Full system name")
        self.assertEqual(feature["properties"]["survey_date"], "2025-01-01")
        self.assertEqual(feature["properties"]["permittee"], "Listed utility")
        self.assertEqual(feature["properties"]["permit_details_date"], "2026-01-01")

    def test_npdes_and_other_numbers_are_retained_without_inferred_ownership(self):
        definition, payload = fixture()
        p = payload["features"][0]["properties"]
        p.update(sop_tracking_number="Other", SOP_Other="TN0078379 - Riverstone Estates")
        result = wastewater.normalize_survey(payload, definition, {})["features"][0]["properties"]
        self.assertEqual(result["permit_number"], "TN0078379")
        self.assertEqual(result["system_name"], "Riverstone Estates")
        self.assertEqual(result["permittee"], "")
        self.assertEqual(result["permit_details_date"], "")

    def test_invalid_source_does_not_become_empty_success(self):
        definition, payload = fixture()
        for invalid in [{"features": []}, {"features": [payload["features"][0]] * 2}]:
            with self.assertRaises(ValueError):
                wastewater.normalize_survey(invalid, definition, {})
        payload["features"][0]["geometry"]["coordinates"] = [float("nan"), 36]
        with self.assertRaises(ValueError):
            wastewater.normalize_survey(payload, definition, {})
        with self.assertRaises(ValueError):
            wastewater.normalize_survey(payload, {"fields": []}, {})

    def test_only_selected_basic_attributes_are_published(self):
        definition, payload = fixture()
        payload["features"][0]["properties"].update(photos="private.jpg", inspector="Person", notes="Narrative")
        feature = wastewater.normalize_survey(payload, definition, {})["features"][0]
        self.assertFalse({"photos", "inspector", "notes"} & feature["properties"].keys())
        self.assertFalse({"photos", "inspector", "notes"} & set(wastewater.SURVEY_FIELDS))

    def test_inaccessible_permit_service_retains_details_while_survey_updates(self):
        definition, survey = fixture()
        old = {"permits": {"SOP-11001": {"PERMITTEE_NAME": "Previous utility"}},
               "retrievedAt": "2025-06-01"}
        with tempfile.TemporaryDirectory() as folder:
            cache, details = Path(folder) / "survey.json", Path(folder) / "details.json"
            wastewater.write_json(details, old)
            with patch.object(wastewater, "CACHE_PATH", cache), patch.object(wastewater, "DETAIL_PATH", details), \
                 patch.object(wastewater.requests, "Session"), \
                 patch.object(wastewater, "request_json", side_effect=[definition, {"count": 1}]), \
                 patch.object(wastewater, "fetch_paged_geojson", side_effect=[survey, RuntimeError("403 Forbidden")]), \
                 patch.object(wastewater, "county_payloads"), patch.object(wastewater, "apply_cached"):
                errors = wastewater.refresh.__wrapped__()
            self.assertEqual(len(errors), 1)
            saved = wastewater.read_json(details)
            self.assertEqual(saved["permits"], old["permits"])
            self.assertEqual(saved["retrievedAt"], "2025-06-01")
            self.assertEqual(saved["refreshStatus"], "Refresh failed; previous data retained")
            self.assertEqual(wastewater.read_json(cache)["features"][0]["properties"]["permittee"], "Previous utility")

    def test_unassignable_location_stops_before_any_county_is_written(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            path = directory / "county.json"
            wastewater.write_json(path, {"slug": "county", "county": {"features": [{"geometry": {
                "type": "Polygon", "coordinates": [[[-87, 36], [-86, 36], [-86, 37], [-87, 37], [-87, 36]]]}}]}})
            previous = path.read_bytes()
            with patch.object(wastewater, "COUNTY_MAPS_DIR", directory):
                with self.assertRaises(ValueError):
                    wastewater.county_payloads({"retrievedAt": "2026-01-01", "features": [{
                        "id": "SOP-11001", "geometry": {"type": "Point", "coordinates": [-90, 35]}}]})
            self.assertEqual(path.read_bytes(), previous)

    def test_transaction_preserves_partial_refresh_report(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(online.config, "PUBLIC_DATA", Path(folder)):
                self.assertEqual(online.transaction(lambda: ["Permit source unavailable"]), ["Permit source unavailable"])


if __name__ == "__main__":
    unittest.main()
