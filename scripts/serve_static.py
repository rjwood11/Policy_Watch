"""Serve the Next.js static export with clean URL fallbacks."""

from __future__ import annotations

import argparse
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse


class NextExportRequestHandler(SimpleHTTPRequestHandler):
    """Map extensionless Next export routes to their generated .html files."""

    def resolve_export_path(self) -> tuple[Path, HTTPStatus]:
        base_dir = Path(self.directory).resolve()
        request_path = PurePosixPath(unquote(urlparse(self.path).path))
        parts = [part for part in request_path.parts if part not in {"", "/"}]

        if any(part in {".", ".."} for part in parts):
            return base_dir / "404.html", HTTPStatus.NOT_FOUND

        if not parts:
            return base_dir / "index.html", HTTPStatus.OK

        candidate = base_dir.joinpath(*parts)

        if candidate.is_file():
            return candidate, HTTPStatus.OK

        if candidate.suffix == "":
            html_candidate = candidate.with_suffix(".html")
            if html_candidate.is_file():
                return html_candidate, HTTPStatus.OK

        index_candidate = candidate / "index.html"
        if index_candidate.is_file():
            return index_candidate, HTTPStatus.OK

        return base_dir / "404.html", HTTPStatus.NOT_FOUND

    def send_head(self):  # type: ignore[override]
        resolved_path, status = self.resolve_export_path()

        if not resolved_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            file_handle = resolved_path.open("rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        stats = os.fstat(file_handle.fileno())
        self.send_response(status)
        self.send_header("Content-type", self.guess_type(str(resolved_path)))
        self.send_header("Content-Length", str(stats.st_size))
        self.send_header("Last-Modified", self.date_time_string(stats.st_mtime))
        self.end_headers()
        return file_handle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the exported PolicyWatch site locally.")
    parser.add_argument("--directory", default="out", help="Static export directory to serve.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=3000, help="Port to bind.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    directory = Path(args.directory).resolve()

    if not directory.is_dir():
        raise SystemExit(f"Static export directory was not found: {directory}")

    handler_class = lambda *handler_args, **handler_kwargs: NextExportRequestHandler(
        *handler_args,
        directory=str(directory),
        **handler_kwargs,
    )

    server = ThreadingHTTPServer((args.host, args.port), handler_class)
    print(f"Serving {directory} at http://{args.host}:{args.port}", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping PolicyWatch static server.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
