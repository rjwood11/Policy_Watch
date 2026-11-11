"""Atomic local data writes with bounded retries for transient Windows locks."""
from __future__ import annotations

import os
import shutil
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


def retry_file_operation(action):
    for attempt in range(5):
        try:
            return action()
        except OSError as exc:
            transient = (isinstance(exc, PermissionError)
                         or getattr(exc, "winerror", None) in {5, 32, 33, 1224}
                         or (os.name == "nt" and exc.errno == 22))
            if attempt == 4 or not transient:
                raise
            time.sleep(0.2 * (2 ** attempt))


@contextmanager
def atomic_output(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{uuid.uuid4().hex}.tmp{path.suffix}")
    try:
        yield temporary
        retry_file_operation(lambda: temporary.replace(path))
    finally:
        retry_file_operation(lambda: temporary.unlink(missing_ok=True))


def write_text_atomic(path: Path, text: str) -> None:
    with atomic_output(path) as temporary:
        temporary.write_text(text, encoding="utf8")


def write_bytes_atomic(path: Path, content: bytes) -> None:
    with atomic_output(path) as temporary:
        temporary.write_bytes(content)


def copy_file_atomic(source: Path, destination: Path):
    with atomic_output(Path(destination)) as temporary:
        retry_file_operation(lambda: shutil.copy2(source, temporary))
    return destination
