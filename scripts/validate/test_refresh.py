"""Regression checks for download failures, pagination, and truthful dates."""
import tempfile
import os
import traceback
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.refresh import online_sources as online
from scripts.refresh import weekly_layers as weekly
from scripts.download import data_fetchers
from scripts.refresh import landuse
from scripts.refresh import census
from scripts.summaries import county_contracts
import geopandas as gpd
import numpy as np
from rasterio.io import MemoryFile
from shapely.geometry import box
import requests


class RefreshTests(unittest.TestCase):
    def test_census_key_stays_local_and_environment_takes_precedence(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / ".env.local").write_text('CENSUS_API_KEY="local-test-key"\n')
            with patch.object(data_fetchers, "ROOT", directory), patch.dict(os.environ, {"CENSUS_API_KEY": ""}):
                self.assertEqual(data_fetchers.census_api_key(), "local-test-key")
                with patch.dict(os.environ, {"CENSUS_API_KEY": "environment-test-key"}):
                    self.assertEqual(data_fetchers.census_api_key(), "environment-test-key")

    def test_census_requires_complete_valid_county_values(self):
        frame = census.pd.DataFrame({"geoid": ["47001", "47003"], "population": [100, 200], "poverty_rate": [10.5, 20.0]})
        census.validate_acs(frame, {"47001", "47003"})
        with self.assertRaises(ValueError):
            census.validate_acs(frame.iloc[:1], {"47001", "47003"})
        with self.assertRaises(ValueError):
            census.validate_acs(census.pd.concat([frame, frame.iloc[:1]]), {"47001", "47003"})
        for column, bad_value in [("population", -1), ("poverty_rate", float("nan")), ("poverty_rate", 101)]:
            bad = frame.copy()
            bad.loc[0, column] = bad_value
            with self.assertRaises(ValueError):
                census.validate_acs(bad, {"47001", "47003"})

    def test_congressional_download_requires_complete_official_plan(self):
        frame = gpd.GeoDataFrame({
            "DISTRICT": list(range(1, 10)),
            "LONGNAME": [f"District {i}" for i in range(1, 10)],
            "TOTAL": [767871] * 9,
        }, geometry=[box(-90 + i / 10, 35, -89.9 + i / 10, 36) for i in range(9)], crs="EPSG:4326")
        session = Mock()
        session.get.return_value.content = b"official-zip"
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(data_fetchers, "RAW_DIR", Path(folder)), \
                 patch.object(data_fetchers.gpd, "read_file", return_value=frame) as read:
                result = data_fetchers.download_congressional_districts(session)
                self.assertEqual(set(result.DISTRICT), {str(i) for i in range(1, 10)})
                self.assertEqual(result.iloc[0]["NAME"], "District 1")
                self.assertEqual(result.iloc[0]["POPULATION"], 767871)
                read.return_value = frame.iloc[:8].copy()
                with self.assertRaises(ValueError):
                    data_fetchers.download_congressional_districts(session)

    def test_missing_landfill_overlay_does_not_abort_county_clipping(self):
        unavailable = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        locations = county_contracts._prepare_landfill_locations(unavailable)
        county = gpd.GeoDataFrame(geometry=[box(-87, 35, -86, 36)], crs="EPSG:4326")
        result = county_contracts._clip_to_county_context(
            locations, county, simplify_meters=100,
            keep_columns=["landfill_id", "landfill_name", "permit_count"],
        )
        self.assertTrue(result.empty)
        self.assertEqual(list(result.columns), ["landfill_id", "landfill_name", "permit_count", "geometry"])
        self.assertEqual(county_contracts._feature_collection(result)["features"], [])

    def test_landcover_uses_explicit_year_and_validates_categorical_raster(self):
        with MemoryFile() as memory:
            with memory.open(driver="GTiff", width=2, height=2, count=1,
                             dtype="uint8", crs="EPSG:3857",
                             transform=landuse.rasterio.transform.from_origin(0, 600, 300, 300)) as raster:
                raster.write(np.array([[11, 21], [41, 81]], dtype="uint8"), 1)
            raster_bytes = memory.read()
        response = Mock(content=raster_bytes)
        counties = gpd.GeoDataFrame(geometry=[box(0, 0, 600, 600)], crs="EPSG:3857")
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "subset.tif"
            with patch.object(landuse, "CACHE_PATH", cache), patch.object(landuse, "RAW_DIR", cache.parent), \
                 patch.object(landuse.requests, "get", return_value=response) as fetch:
                landuse.download_subset(counties, force=True)
                params = fetch.call_args.kwargs["params"]
                self.assertEqual(params["version"], "1.0.0")
                self.assertEqual(params["time"], f"{landuse.YEAR}-01-01T00:00:00.000Z")
                with landuse.rasterio.open(cache) as raster:
                    self.assertEqual(raster.read(1).tolist(), [[11, 21], [41, 81]])
                response.content = b"<ExceptionReport>Unavailable</ExceptionReport>"
                response.text = response.content.decode()
                previous = cache.read_bytes()
                with self.assertRaises(ValueError):
                    landuse.download_subset(counties, force=True)
                self.assertEqual(cache.read_bytes(), previous)

    def test_total_failure_is_not_reported_as_partial_refresh(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            weekly.write_json(directory / "data-sources.json", [{
                "dataset": "TDEC DWR public water resources permits", "lastUpdated": "2026-01-01",
            }])
            results = [{"slug": "a", "tdec": {"status": "error"}, "echo": {"status": "skipped"}}]
            with patch.object(weekly, "METADATA_DIR", directory), patch.object(weekly, "WEEKLY_DIR", directory):
                weekly.update_source_metadata("2026-11-11", results)
            source = weekly.read_json(directory / "data-sources.json")[0]
            self.assertEqual(source["refreshStatus"], "Refresh failed; previous data retained")
            self.assertEqual(source["lastUpdated"], "2026-01-01")

    def test_census_errors_do_not_publish_api_key(self):
        with patch.object(data_fetchers.requests, "get", side_effect=requests.ConnectionError("URL?key=private-key")):
            with self.assertRaises(RuntimeError) as error:
                data_fetchers.load_acs()
        self.assertNotIn("private-key", str(error.exception))
        self.assertNotIn("private-key", "".join(traceback.format_exception(error.exception)))

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
            self.assertEqual(fetch.call_args.kwargs["params"]["resultOffset"], "1")

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
