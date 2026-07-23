# Weekly generated layers

GitHub Actions writes EPA ECHO CWA compliance and TDEC DWR public permit cache files here before building the static site.

ECHO violation files are committed under `public/data/weekly/{county}/echo-violations.geojson`.
They are small, change infrequently, and give the county maps a last-good layer when the EPA ECHO
service is slow or unavailable.

TDEC permit files remain ignored by git because they are larger and change more often. County maps
load cached files first and fall back to the public services at runtime only when a cache file is
missing.
