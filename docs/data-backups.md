# Local source-data history

Every data refresh/build command now preserves a snapshot **before** changing data and another snapshot **after** it finishes. Failed commands preserve their before/after state too. The snapshots include `public/data/`, all local GIS inputs and shapefile companion files in `data/external/`, downloaded inputs in `data/raw/`, the legislator lookup, and Python requirements. Environmental, district, and Census refreshes share this behavior; a normal website-only `npm run build` does not download or refresh data.

Validated downloads are also saved before simplification, county clipping, ECHO filtering, or land-cover reclassification. The source history covers Census TIGER ZIPs and original ACS API rows, USGS watersheds, state districts, the official congressional shapefile ZIP, drinking-water areas, service-line inventories, landfills, protected areas, original Superfund features, ECHO responses, TDEC permit features, and the downloaded Annual NLCD GeoTIFF subset. Local GIS snapshots, road/river/city inputs, current elected-official names, and their saved source notes are included in the file snapshots.

The full online refresh additionally downloads the Tennessee ATTAINS river dataset, rather than just checking service availability. All pages must finish before the combined GeoJSON is saved. Requests that fail, return agency errors, or stop pagination early do not become successful source-download records. Existing local data and all previous archived versions remain available.

## Location and retention

The archive is local at `data/archives/`, outside `public/`, and ignored by Git:

```
data/archives/
  objects/<SHA-256 checksum>           # original file/download bytes
  runs/<UTC timestamp>-<unique ID>/
    before.json                       # file paths, sizes, checksums
    after.json                        # resulting files and refresh state
    sources/<unique ID>.json           # source URL, request scope, time, checksum
```

There is **no automatic deletion or expiration for local history**. Identical contents share one stored object; changed versions are retained separately, even if multiple refreshes happen on the same day. The archive records when bytes were captured, which is distinct from the agency's publication date and the successful-refresh dates in saved metadata. The before/after manifests preserve enough information to put files back at their original relative paths. A completed command can still have source failures: consult its archived `refresh-run.json`, weekly manifest, and dataset refresh statuses.

Each local command verifies the checksums for its snapshots and source downloads. If the initial preservation snapshot cannot be saved or verified, the refresh stops before modifying data. API keys are removed from request metadata. `.env` files, credentials, dependencies, Git files, browser caches, and general local Codex files are excluded. This is a data archive, so keep a separate secure copy of credentials and the source-code repository.

Copy the **entire `data/archives` directory**, including both `objects` and `runs`, to another drive or backup service for a second copy. Individual manifests alone do not contain the underlying file bytes.

## Inspect, verify, and recover

Run these commands from the PolicyWatch project folder:

```powershell
npm run data:archive-list
npm run data:archive-verify
npm run data:archive
```

The last command creates an extra snapshot without contacting agency services. Use it before manually replacing GIS inputs. Existing snapshots are not relabeled as new agency downloads.

To recover a chosen before/after version into a **new directory**:

```powershell
python -m scripts.common.source_archive restore --manifest "data/archives/runs/RUN-ID/after.json" --destination "data/restored/recovered-version"
```

Replace `RUN-ID` with one shown by `data:archive-list`. Recovery verifies the objects before copying any files, rejects unsafe paths, and refuses to overwrite an existing destination. Inspect the recovered data before deliberately copying it back into the working application. The application is not changed by the recovery command.

To recover an individual original agency download, use one of that run's `sources/*.json` manifests with the same command and a new destination directory. Those manifests identify their source URL and query scope; GeoJSON collections, Census rows, ZIPs, and GeoTIFFs retain their original source representation.

## Refreshes on GitHub

The deployment and manual ECHO workflows have been configured to verify and upload `data/archives/` as a separate downloadable Actions artifact, including after partial failures. This does not publish the archive on the website or commit it to Git. These workflow changes take effect when the owner publishes them.

Artifacts are configured for **90 days of retention**, subject to the repository's allowed retention limit. GitHub runners are temporary machines; their disk files do not automatically appear on this computer. Download the source-archive artifact from a workflow run and extract it before it expires, then merge it into permanent local history:

```powershell
python -m scripts.common.source_archive import --source "C:/Downloads/extracted-source-archive"
```

Point `--source` at the extracted directory containing `objects/` and `runs/`. Import verifies all referenced objects, deduplicates file contents, keeps existing local versions, and rejects conflicting run manifests. Keep the source artifact until the import verifies successfully.

## Live-service limits

ATTAINS data can be recovered from the saved Tennessee GeoJSON even if EPA removes that endpoint. The browser's existing fallback still uses the local TDEC impairment layer; recovery of the archived EPA snapshot is a separate operation, and the archive does not change which overlay the browser uses.

The TNMap address locator's service definition is archived, but its private search index cannot be exported through that endpoint. Individual addresses entered by users are not logged or archived. OpenStreetMap background tiles and externally hosted fonts are presentation services, not the saved environmental datasets; this backup does not mirror their global tile/font catalogs. Those services would need a replacement provider or a separately licensed offline package if discontinued. The locally stored environmental geometries, summaries, and source history are independent of them.

The full online refresh also archives the official-directory and election-result pages cited by `legislative-update.json`. Those reference documents are evidence snapshots; collecting them does not automatically verify new elections, change the reviewed roster, or fill future vacancies. Continue to review member names separately from boundary refreshes.
