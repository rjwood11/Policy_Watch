"""Local, content-addressed source history. Never store credentials or auto-delete history."""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from scripts.common import prototype_config as config
from scripts.common.file_io import retry_file_operation

ARCHIVE_ROOT = config.ROOT / "data" / "archives"
RUN_ENV = "POLICYWATCH_ARCHIVE_RUN"
SECRET_FIELDS = {"key", "apikey", "api_key", "token", "access_token", "authorization", "password", "secret"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize(value):
    if isinstance(value, dict):
        return {str(key): "[redacted]" if str(key).lower() in SECRET_FIELDS else sanitize(item)
                for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    if isinstance(value, str) and value.startswith(("https://", "http://")):
        parts = urlsplit(value)
        # Credentials in URL userinfo must not survive either.
        host = parts.netloc.rsplit("@", 1)[-1]
        query = [(key, "[redacted]" if key.lower() in SECRET_FIELDS else item)
                 for key, item in parse_qsl(parts.query, keep_blank_values=True)]
        return urlunsplit((parts.scheme, host, parts.path, urlencode(query), ""))
    return value


def write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    retry_file_operation(lambda: temporary.replace(path))


def run_directory() -> Path | None:
    run_id = os.getenv(RUN_ENV)
    if not run_id:
        return None
    if not re.fullmatch(r"[0-9TZ-]+-[a-f0-9]{12}", run_id):
        raise ValueError("Invalid archive run identifier")
    return ARCHIVE_ROOT / "runs" / run_id


def store_file(path: Path) -> dict:
    return retry_file_operation(lambda: _store_file(path))


def _store_file(path: Path) -> dict:
    digest = hashlib.sha256()
    directory = ARCHIVE_ROOT / "objects"
    directory.mkdir(parents=True, exist_ok=True)
    # Hash the copy, so a concurrent source-file change cannot create a wrong
    # checksum. Separate temporary files make county workers/processes safe.
    with tempfile.NamedTemporaryFile(dir=directory, delete=False) as output:
        temporary = Path(output.name)
        try:
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
                    output.write(chunk)
        except BaseException:
            output.close()
            temporary.unlink(missing_ok=True)
            raise
    checksum = digest.hexdigest()
    target = directory / checksum
    try:
        if not target.exists():
            # Atomic create without replacing an immutable existing object.
            try:
                retry_file_operation(lambda: os.link(temporary, target))
            except FileExistsError:
                pass
        return {"sha256": checksum, "bytes": temporary.stat().st_size}
    finally:
        retry_file_operation(lambda: temporary.unlink(missing_ok=True))


def archive_file(source: str, path: Path, *, url: str = "", params=None, kind="validated-download") -> None:
    directory = run_directory()
    if directory is None:
        return
    item = store_file(path)
    write_manifest(directory / "sources" / f"{uuid.uuid4().hex}.json", {
        "version": 1, "source": source, "capturedAt": now(), "kind": kind,
        "filename": path.name, "sourceUrl": sanitize(url), "request": sanitize(params or {}), **item,
    })


def archive_bytes(source: str, content: bytes, *, filename: str, url: str = "", params=None, kind="validated-download") -> None:
    if run_directory() is None:
        return
    # Only a simple filename is accepted, never a caller-provided path.
    with tempfile.TemporaryDirectory(prefix="policywatch-source-") as folder:
        path = Path(folder) / Path(filename).name
        path.write_bytes(content)
        archive_file(source, path, url=url, params=params, kind=kind)


def archive_json(source: str, payload, *, url: str = "", params=None, kind="validated-download") -> None:
    archive_bytes(source, json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf8"),
                  filename="source.geojson" if isinstance(payload, dict) and payload.get("type") == "FeatureCollection" else "source.json",
                  url=url, params=params, kind=kind)


def snapshot(phase: str, *, label: str, status: str) -> Path:
    directory = run_directory()
    if directory is None:
        raise ValueError("No active archive run")
    files = []
    roots = [config.PUBLIC_DATA, config.EXTERNAL_DIR, config.RAW_DIR,
             config.ROOT / "src" / "lib" / "tennesseeLegislators.ts",
             config.ROOT / "requirements.txt"]
    for root in roots:
        candidates = sorted(root.rglob("*")) if root.is_dir() else [root]
        for path in candidates:
            if not path.is_file() or path.is_symlink() or path.suffix in {".tmp", ".pyc"}:
                continue
            relative = path.resolve().relative_to(config.ROOT.resolve())
            sensitive_path = re.search(r"(?:^|[/_.-])(credentials?|secrets?|tokens?|api[_-]?key|password)(?:$|[/_.-])",
                                       relative.as_posix(), re.I)
            if any(part.startswith(".") for part in relative.parts) or sensitive_path:
                continue
            files.append({"path": relative.as_posix(), **store_file(path)})
    path = directory / f"{phase}.json"
    sources_path = config.METADATA_DIR / "data-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf8")) if sources_path.is_file() else []
    write_manifest(path, {"version": 1, "label": label, "phase": phase, "status": status,
                          "capturedAt": now(), "files": files,
                          "datasets": [{key: source[key] for key in ("dataset", "lastUpdated", "refreshStatus") if key in source}
                                       for source in sources]})
    return path


def archived_refresh(label: str):
    """Archive before/after each command; nested builders share the outer run."""
    def decorate(action):
        @functools.wraps(action)
        def wrapped(*args, **kwargs):
            if run_directory() is not None:
                return action(*args, **kwargs)
            run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
            os.environ[RUN_ENV] = run_id
            try:
                snapshot("before", label=label, status="before-refresh")
                verify(ARCHIVE_ROOT, run_id=run_id)
                try:
                    result = action(*args, **kwargs)
                except BaseException:
                    snapshot("after", label=label, status="command-failed; inspect saved refresh reports")
                    raise
                path = snapshot("after", label=label, status="command-finished; inspect saved refresh reports")
                verify(ARCHIVE_ROOT, run_id=run_id)
                print(f"Local source archive: {path.relative_to(config.ROOT)}", flush=True)
                return result
            finally:
                os.environ.pop(RUN_ENV, None)
        return wrapped
    return decorate


def verify(root: Path = ARCHIVE_ROOT, *, run_id: str | None = None) -> tuple[int, int]:
    checked = {}
    manifests = list(((root / "runs" / run_id) if run_id else (root / "runs")).rglob("*.json"))
    if not manifests:
        raise ValueError("Archive has no manifests")
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf8"))
        items = manifest.get("files", [manifest] if "sha256" in manifest else [])
        for item in items:
            checksum = item["sha256"]
            if not re.fullmatch(r"[a-f0-9]{64}", checksum):
                raise ValueError("Invalid archive checksum")
            if checksum not in checked:
                obj = root / "objects" / checksum
                if not obj.is_file():
                    raise ValueError(f"Missing or damaged archive object: {checksum}")
                with obj.open("rb") as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != checksum:
                        raise ValueError(f"Missing or damaged archive object: {checksum}")
                checked[checksum] = obj.stat().st_size
            if checked[checksum] != item["bytes"]:
                raise ValueError(f"Archive size mismatch: {checksum}")
    return len(manifests), len(checked)


def restore(manifest_path: Path, destination: Path, *, root: Path = ARCHIVE_ROOT) -> int:
    """Recover a snapshot into a new directory; never overwrite the working app."""
    if destination.exists():
        raise ValueError("Restore destination must be a new directory")
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    files = manifest.get("files", [{"path": manifest.get("filename", "source.json"), **manifest}]
                         if "sha256" in manifest else [])
    if not files:
        raise ValueError("Select a before/after snapshot or a source-download manifest")
    planned = []
    for item in files:
        relative = Path(item["path"])
        target = (destination / relative).resolve()
        if relative.is_absolute() or not target.is_relative_to(destination.resolve()):
            raise ValueError("Unsafe restore path")
        checksum = item["sha256"]
        if not re.fullmatch(r"[a-f0-9]{64}", checksum):
            raise ValueError("Invalid archive checksum")
        obj = root / "objects" / checksum
        with obj.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != checksum or obj.stat().st_size != item["bytes"]:
                raise ValueError(f"Damaged archive object: {checksum}")
        planned.append((obj, target))
    for obj, target in planned:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(obj, target)
    return len(planned)


def import_archive(source: Path) -> tuple[int, int]:
    """Merge a downloaded Actions artifact without losing local history."""
    if source.resolve() == ARCHIVE_ROOT.resolve():
        raise ValueError("Source archive is already the local archive")
    verify(source)
    manifests = list((source / "runs").rglob("*.json"))
    objects = set()
    planned = []
    for path in manifests:
        relative = path.relative_to(source / "runs")
        if path.is_symlink() or not re.fullmatch(r"[0-9TZ-]+-[a-f0-9]{12}", relative.parts[0]):
            raise ValueError("Unsafe imported run path")
        target = ARCHIVE_ROOT / "runs" / relative
        if target.exists() and target.read_bytes() != path.read_bytes():
            raise ValueError("An imported run conflicts with local history")
        payload = json.loads(path.read_text(encoding="utf8"))
        objects.update(item["sha256"] for item in payload.get("files", [payload] if "sha256" in payload else []))
        planned.append((path, target))
    for checksum in sorted(objects):
        store_file(source / "objects" / checksum)
    for path, target in planned:
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    return verify(ARCHIVE_ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["snapshot", "verify", "list", "restore", "import"])
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.action == "snapshot":
        archived_refresh("Manual preservation snapshot")(lambda: None)()
    elif args.action == "verify":
        manifests, objects = verify()
        print(f"Verified {manifests} manifests and {objects} unique archive objects.")
    elif args.action == "list":
        for path in sorted((ARCHIVE_ROOT / "runs").glob("*/after.json")):
            value = json.loads(path.read_text(encoding="utf8"))
            downloads = len(list((path.parent / "sources").glob("*.json")))
            print(path.parent.name, value["label"], f"({len(value['files'])} saved files; {downloads} source records)", value["status"])
    elif args.action == "import":
        if not args.source:
            parser.error("import requires --source pointing to the extracted artifact's objects/runs directory")
        manifests, objects = import_archive(args.source)
        print(f"Imported history. Verified {manifests} manifests and {objects} unique objects.")
    else:
        if not args.manifest or not args.destination:
            parser.error("restore requires --manifest and --destination")
        print(f"Restored {restore(args.manifest, args.destination)} files into {args.destination}.")


if __name__ == "__main__":
    main()
