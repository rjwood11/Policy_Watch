"""Regression checks for download failures, pagination, and truthful dates."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.refresh import online_sources as online
from scripts.refresh import weekly_layers as weekly
from scripts.download import data_fetchers
import requests


class RefreshTests(unittest.TestCase):
    def test_census_errors_do_not_publish_api_key(self):
        with patch.object(data_fetchers.requests, "get", side_effect=requests.ConnectionError("URL?key=private-key")):
            with self.assertRaises(RuntimeError) as error:
                data_fetchers.load_acs()
        self.assertNotIn("private-key", str(error.exception))

    def test_arcgis_error_cannot_erase_cache(self):
        with patch.object(weekly, "request_json", return_value={"error": {"message": "Unavailable"}}):
            with self.assertRaises(ValueError):
                weekly.fetch_paged_geojson(Mock(), "https://example.test/query", {})

    def test_short_page_with_transfer_limit_continues(self):
        page = {"type": "FeatureCollection", "features": [{"type": "Feature"}], "properties": {"exceededTransferLimit": True}}
        final = {"type": "FeatureCollection", "features": []}
        with patch.object(weekly, "request_json", side_effect=[page, final]) as fetch:
            result = weekly.fetch_paged_geojson(Mock(), "https://example.test/query", {})
            self.assertEqual(len(result["features"]), 1)
            self.assertEqual(fetch.call_count, 2)

    def test_pagination_limit_is_failure(self):
        page = {"type": "FeatureCollection", "features": [{}], "exceededTransferLimit": True}
        with patch.object(weekly, "request_json", return_value=page):
            with self.assertRaises(ValueError):
                weekly.fetch_paged_geojson(Mock(), "https://example.test/query", {}, max_pages=1)

    def test_malformed_echo_is_not_empty_success(self):
        for payload in [{}, {"Results": {"Error": "Unavailable"}}, None]:
            with self.assertRaises(ValueError):
                weekly.echo_facility_collection(payload)
        self.assertEqual(weekly.echo_facility_collection({"Results": {"QueryRows": "0"}})["features"], [])

    def test_echo_column_drift_cannot_clear_violation_cache(self):
        with self.assertRaises(ValueError):
            weekly.facilities_to_feature_collection({"Results": {"Facilities": [{"CWPName": "Example"}]}})

    def test_echo_named_fields_keep_compliance_and_coordinates(self):
        result = weekly.facilities_to_feature_collection({"Results": {"Facilities": [{
            "CWPName": "Example", "FacLat": "36", "FacLong": "-86", "CWPQtrsWithNC": "2",
            "SourceID": "TN123", "UnneededField": "discard",
        }]}})
        normalized = weekly.normalize_echo_collection(result)
        self.assertEqual(len(normalized["features"]), 1)
        self.assertEqual(normalized["features"][0]["properties"]["echo_violation_count"], 2)
        self.assertNotIn("UnneededField", normalized["features"][0]["properties"])

    def test_partial_counties_do_not_advance_statewide_date(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            weekly.write_json(directory / "last-updated.json", {"tdec-dwr-public-permits": "2026-01-01"})
            weekly.write_json(directory / "data-sources.json", [{"dataset": "TDEC DWR public water resources permits", "lastUpdated": "2026-01-01"}])
            results = [{"slug": "a", "tdec": {"status": "ok"}, "echo": {"status": "skipped"}},
                       {"slug": "b", "tdec": {"status": "error"}, "echo": {"status": "skipped"}}]
            with patch.object(weekly, "METADATA_DIR", directory), patch.object(weekly, "WEEKLY_DIR", directory):
                weekly.update_source_metadata("2026-10-15", results)
                source = weekly.read_json(directory / "data-sources.json")[0]
                self.assertEqual(source["lastUpdated"], "2026-01-01")
                self.assertEqual(source["lastChecked"], "2026-10-15")
                self.assertEqual(results[0]["tdec"]["lastSuccessfulRefresh"], "2026-10-15")

    def test_transaction_restores_files_and_removes_new_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / "previous.json").write_text("original")
            def broken():
                (directory / "previous.json").write_text("changed")
                (directory / "new.json").write_text("new")
                raise ValueError("Build failed")
            with patch.object(online.config, "PUBLIC_DATA", directory):
                with self.assertRaises(ValueError):
                    online.transaction(broken)
            self.assertEqual((directory / "previous.json").read_text(), "original")
            self.assertFalse((directory / "new.json").exists())

    def test_census_outage_does_not_select_older_release(self):
        session = Mock()
        response = session.get.return_value
        response.status_code = 503
        response.raise_for_status.side_effect = RuntimeError("Service unavailable")
        with self.assertRaises(RuntimeError):
            online.latest_census(session, "acs")
        self.assertEqual(session.get.call_count, 1)

    def test_validation_exit_rolls_back_and_allows_other_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            path = directory / "county.json"
            path.write_text("previous")
            def invalid_build():
                path.write_text("invalid")
                raise SystemExit("Invalid county data")
            with patch.object(online.config, "PUBLIC_DATA", directory):
                with self.assertRaises(RuntimeError):
                    online.transaction(invalid_build)
            self.assertEqual(path.read_text(), "previous")


if __name__ == "__main__":
    unittest.main()
