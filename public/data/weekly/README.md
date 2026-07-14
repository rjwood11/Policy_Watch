# Weekly generated layers

GitHub Actions writes EPA ECHO CWA compliance and TDEC DWR public permit cache files here before building the static site.

The generated GeoJSON files are ignored by git so the repository stays small. County maps fall back to the public services at runtime when these files are missing.
