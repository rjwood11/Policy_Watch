"""Archive durability, recovery, concurrency, and credential exclusion checks."""
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.common import source_archive as archive
from scripts.common import file_io
from scripts.refresh import weekly_layers


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.store = self.root / "data" / "archives"
        for name, value in [("ROOT", self.root), ("PUBLIC_DATA", self.root / "public" / "data"),
                            ("METADATA_DIR", self.root / "public" / "data" / "metadata"),
                            ("EXTERNAL_DIR", self.root / "data" / "external"),
                            ("RAW_DIR", self.root / "data" / "raw")]:
            patcher = patch.object(archive.config, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(archive, "ARCHIVE_ROOT", self.store)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop(archive.RUN_ENV, None)
        self.public = archive.config.PUBLIC_DATA
        self.public.mkdir(parents=True)
        (self.public / "layer.json").write_text('{"value":"original"}')

    def activate(self):
        os.environ[archive.RUN_ENV] = "20261111T120000Z-0123456789ab"

    def test_failed_refresh_preserves_before_and_after_snapshots(self):
        @archive.archived_refresh("Broken refresh")
        def broken():
            (self.public / "layer.json").write_text('{"value":"changed"}')
            raise ValueError("Upstream failed")
        with self.assertRaises(ValueError):
            broken()
        before = next((self.store / "runs").glob("*/before.json"))
        after = before.with_name("after.json")
        self.assertIn("command-failed", json.loads(after.read_text())["status"])
        destination = self.root / "recovered"
        archive.restore(before, destination, root=self.store)
        self.assertEqual((destination / "public/data/layer.json").read_text(), '{"value":"original"}')
        self.assertNotIn(archive.RUN_ENV, os.environ)
        archive.verify(self.store)

    def test_unchanged_runs_keep_history_and_share_objects(self):
        action = archive.archived_refresh("Unchanged refresh")(lambda: None)
        action()
        action()
        self.assertEqual(len(list((self.store / "runs").glob("*/after.json"))), 2)
        self.assertEqual(len(list((self.store / "objects").iterdir())), 1)

    def test_concurrent_downloads_do_not_overwrite_source_records(self):
        self.activate()
        with ThreadPoolExecutor(max_workers=6) as workers:
            list(workers.map(lambda _: archive.archive_json("Example", {"rows": [1, 2, 3]}), range(12)))
        self.assertEqual(len(list((archive.run_directory() / "sources").glob("*.json"))), 12)
        self.assertEqual(len(list((self.store / "objects").iterdir())), 1)
        archive.verify(self.store)

    def test_request_credentials_and_local_environment_are_excluded(self):
        self.activate()
        (self.root / ".env.local").write_text("CENSUS_API_KEY=private-test-key")
        archive.config.RAW_DIR.mkdir(parents=True)
        (archive.config.RAW_DIR / "CENSUS_API_KEY.txt").write_text("private-test-key")
        (archive.config.RAW_DIR / "credentials.json").write_text('"private-test-key"')
        archive.archive_json("Census", {"rows": [1]}, url="https://user:private-test-key@example.test/data?key=private-test-key&year=2024",
                             params={"key": "private-test-key", "nested": {"access_token": "private-test-key"}})
        archive.snapshot("after", label="Test", status="finished")
        for path in self.store.rglob("*"):
            if path.is_file():
                self.assertNotIn(b"private-test-key", path.read_bytes())

    def test_corruption_is_detected_before_restoring_files(self):
        self.activate()
        manifest = archive.snapshot("after", label="Test", status="finished")
        item = json.loads(manifest.read_text())["files"][0]
        (self.store / "objects" / item["sha256"]).write_bytes(b"damaged")
        with self.assertRaises(ValueError):
            archive.verify(self.store)
        destination = self.root / "recovered"
        with self.assertRaises(ValueError):
            archive.restore(manifest, destination, root=self.store)
        self.assertFalse(destination.exists())

    def test_restore_rejects_overwrite_and_path_traversal(self):
        self.activate()
        manifest = archive.snapshot("after", label="Test", status="finished")
        with self.assertRaises(ValueError):
            archive.restore(manifest, self.public, root=self.store)
        payload = json.loads(manifest.read_text())
        payload["files"][0]["path"] = "../escaped.json"
        manifest.write_text(json.dumps(payload))
        with self.assertRaises(ValueError):
            archive.restore(manifest, self.root / "recovered", root=self.store)
        self.assertFalse((self.root / "escaped.json").exists())

    def test_individual_source_can_be_restored_without_its_remote_service(self):
        self.activate()
        archive.archive_bytes("County archive", b"original agency bytes", filename="counties.zip")
        manifest = next((archive.run_directory() / "sources").glob("*.json"))
        destination = self.root / "recovered"
        archive.restore(manifest, destination, root=self.store)
        self.assertEqual((destination / "counties.zip").read_bytes(), b"original agency bytes")

    def test_error_response_does_not_create_a_successful_source_archive(self):
        self.activate()
        with patch.object(weekly_layers, "request_json", return_value={"error": {"message": "Deleted"}}):
            with self.assertRaises(ValueError):
                weekly_layers.fetch_paged_geojson(Mock(), "https://example.test/query", {})
        self.assertFalse((self.store / "objects").exists())

    def test_downloaded_artifact_can_be_merged_without_discarding_local_history(self):
        archive.archived_refresh("Local refresh")(lambda: None)()
        downloaded = self.root / "downloaded"
        import shutil
        shutil.copytree(self.store, downloaded)
        (self.public / "layer.json").write_text('{"value":"newer"}')
        archive.archived_refresh("Newer local refresh")(lambda: None)()
        archive.import_archive(downloaded)
        self.assertEqual(len(list((self.store / "runs").glob("*/after.json"))), 2)
        self.assertEqual(len(list((self.store / "objects").iterdir())), 2)

    def test_atomic_write_retries_a_lock_and_preserves_previous_file_if_it_persists(self):
        destination = self.public / "layer.json"
        original_replace = Path.replace
        attempts = []
        def replace(path, target):
            attempts.append(path)
            if len(attempts) == 1:
                raise PermissionError("Transient Windows lock")
            return original_replace(path, target)
        with patch.object(Path, "replace", new=replace), patch.object(file_io.time, "sleep"):
            file_io.write_text_atomic(destination, "complete replacement")
        self.assertEqual(len(attempts), 2)
        self.assertEqual(destination.read_text(), "complete replacement")
        with patch.object(Path, "replace", side_effect=PermissionError("Persistent lock")), patch.object(file_io.time, "sleep"):
            with self.assertRaises(PermissionError):
                file_io.write_text_atomic(destination, "must not become visible")
        self.assertEqual(destination.read_text(), "complete replacement")
        self.assertEqual(list(self.public.glob(".*.tmp.json")), [])

    def test_refresh_does_not_run_if_preservation_fails(self):
        action = Mock()
        with patch.object(archive, "snapshot", side_effect=OSError("Disk full")):
            with self.assertRaises(OSError):
                archive.archived_refresh("Test")(action)()
        action.assert_not_called()
        self.assertNotIn(archive.RUN_ENV, os.environ)


if __name__ == "__main__":
    unittest.main()
