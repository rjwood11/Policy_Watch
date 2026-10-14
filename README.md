# PolicyWatch Prototype

Static-first Tennessee environmental dashboard prototype designed for zero-cost GitHub deployment now and a cleaner production migration later.

Temporary chat reference: `CHAT_ID_PLACEHOLDER`

## Goals

- Test a public-facing Tennessee county and watershed dashboard before paying for infrastructure
- Keep all public pages renderable from local exported files
- Preserve data contracts that can later be backed by PostGIS and scheduled ETL

## Stack

- Next.js
- TypeScript
- Tailwind CSS
- MapLibre dependency included for later migration
- Static export for GitHub Pages

## Local Development

```bash
npm install
pip install -r requirements.txt
npm run dev
```

On Windows, you can also double-click [`launch-local.bat`](launch-local.bat) to install dependencies if needed, serve the existing static export, and open the app in your browser. The launcher uses the static export by default because it matches GitHub Pages behavior and starts more reliably for this map-heavy prototype.

Useful launcher flags:

```bat
set POLICYWATCH_REBUILD_STATIC=1
launch-local.bat

set POLICYWATCH_REBUILD_DATA=1
set POLICYWATCH_REBUILD_STATIC=1
launch-local.bat

set POLICYWATCH_LAUNCH_MODE=dev
launch-local.bat
```

From a console, serve the current static export with clean URL support:

```bash
npm run serve:static -- --port 3000
```

If you need a fresh static export first:

```bash
npm run build
npm run serve:static -- --port 3000
```

## Temporary Internet Sharing

Use this when someone needs to explore the local prototype from a different network. This creates a temporary public HTTPS URL that forwards traffic to the app running on your computer.

This setup uses Cloudflare Quick Tunnel. It does not require a Cloudflare account or DNS setup, but it is intended for testing and development only. Anyone with the generated URL can access the app while the tunnel is running.

Reference: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/

1. Build the static export if needed:

```powershell
npm run build
```

2. Start the local static server:

```powershell
python -m scripts.serve_static --directory out --host 127.0.0.1 --port 3000
```

Leave this terminal open. Confirm the app works locally at:

```text
http://127.0.0.1:3000
```

3. In a second terminal, install or download `cloudflared`.

If this prints a version number, `cloudflared` is already installed and you can skip to step 4:

```powershell
cloudflared --version
```

Option A, install with WinGet:

```powershell
winget install --id Cloudflare.cloudflared
```

Option B, download a standalone copy to a temporary folder:

```powershell
$tunnelDir = Join-Path $env:TEMP 'policywatch-tunnel'
New-Item -ItemType Directory -Force -Path $tunnelDir | Out-Null
$cloudflared = Join-Path $tunnelDir 'cloudflared.exe'
curl.exe -L --fail --show-error --output $cloudflared 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe'
& $cloudflared --version
```

4. Start the tunnel.

If `cloudflared` was installed with WinGet:

```powershell
cloudflared tunnel --url http://127.0.0.1:3000
```

If using the standalone download:

```powershell
& $cloudflared tunnel --url http://127.0.0.1:3000
```

5. Copy the generated `https://...trycloudflare.com` URL from the terminal and share it with colleagues.

Keep both terminals open while people are using the app. The URL stops working when either the static server or the tunnel process is closed. If you restart the tunnel, Cloudflare will usually generate a different URL.

To stop sharing, press `Ctrl+C` in both terminals. If the processes were started in the background, find and stop them with:

```powershell
$serverPid = (Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue |
  Where-Object State -eq Listen |
  Select-Object -First 1 -ExpandProperty OwningProcess)
if ($serverPid) { Stop-Process -Id $serverPid -ErrorAction SilentlyContinue }
Stop-Process -Name cloudflared -ErrorAction SilentlyContinue
```

## Static Build

```bash
npm install
npm run build
```

## Rebuild Local Data

```bash
python -m scripts.summaries.build_prototype_data
npm run build
```

The project uses `output: "export"` in `next.config.mjs`, so `next build` emits a static site in `out/`.

## Publish to GitHub and GitHub Pages

PolicyWatch is a static Next.js application: GitHub stores the source, GitHub Actions builds it, and GitHub Pages serves the exported HTML, JavaScript, images, and map data. Your computer can be off after deployment. No Python or Node server runs on GitHub Pages. External map services still require an internet connection and remain subject to their availability.

Repository: [rjwood11/Policy_Watch](https://github.com/rjwood11/Policy_Watch)  
Live application: [PolicyWatch on GitHub Pages](https://rjwood11.github.io/Policy_Watch/)

### Everyday workflow on Windows

1. Use Codex to edit and improve this local folder.
2. Preview locally with `launch-local.bat`. Set `POLICYWATCH_REBUILD_STATIC=1` when you want that launcher to rebuild edited source, or use dev mode.
3. When ready to publish, double-click **`PUBLISH-TO-GITHUB.bat`** in the project root.
4. The launcher runs lint and a production build. It then stages all non-ignored new, modified, and deleted files, asks for an optional commit description (Enter uses a dated message), commits, and pushes `main`.
5. Wait for the deployment in the repository's **Actions** tab to turn green. The Pages URL displays the new version after a successful deployment.

The window stays open so you can read success or error messages. No source changes are uploaded until you launch the publisher. A failed lint/build stops publishing; a failed push preserves the local commit for retry. The publisher never force-pushes or automatically merges remote changes. If GitHub has newer commits, ask Codex to integrate them, then retry. Save editor files before publishing.

Optional console usage:

```powershell
.\PUBLISH-TO-GITHUB.bat -Message "Improve county maps"
.\PUBLISH-TO-GITHUB.bat -CheckOnly
```

`-CheckOnly` validates without staging, committing, or pushing. The script requires Git for Windows and Node.js (22 LTS or newer supported LTS recommended). It uses Git's stored sign-in; no password or access token belongs in the batch file or repository. GitHub CLI is useful for setup, but is not required for everyday publishing.

### One-time repository setup

Create an empty repository (no generated README, license, or .gitignore) in your GitHub account. A public repository supports free GitHub Pages; private repositories require an eligible paid GitHub plan. This repository includes source GIS files in `data/external`, which are uploaded along with the application source. `.env` files, dependencies, generated builds, raw/processed caches, and local Codex caches are ignored. Already tracked files remain tracked regardless of ignore rules.

From this folder, connect the repository and publish:

```powershell
git remote add origin https://github.com/rjwood11/Policy_Watch.git
.\PUBLISH-TO-GITHUB.bat
```

In GitHub, open **Settings > Pages > Build and deployment > Source** and choose **GitHub Actions**. If the first workflow ran before enabling Pages, rerun it from Actions. Keep the default branch as `main`. The usual site URL is `https://rjwood11.github.io/Policy_Watch/` (repository name casing matters).

The deployment workflow reads the Pages base path automatically, so routes, map JSON, cached layers, logos, and land-cover images work under the repository URL. `trailingSlash: true` exports route directories with `index.html` so county/ranking URLs also work when opened directly or refreshed. Local builds use the domain root as before. A future custom domain is supported through the Pages configuration and workflow-provided base path.

### Deployment and data refreshes

- `.github/workflows/deploy.yml` deploys on pushes to `main` and manual runs. It installs locked npm dependencies, lints, builds the static export, and publishes `out/` as a Pages artifact. There are no scheduled deployments.
- `.github/workflows/ci.yml` checks pull requests and manual runs, including a build with a repository URL prefix.
- Normal deployments use committed data. The optional manual `refresh_live_layers` input refreshes EPA ECHO and TDEC caches in the deployment artifact. It defaults off to keep publishing independent of refresh-service availability.
- `.github/workflows/refresh-echo-cache.yml` is manual only. Running it commits updated ECHO cache data to GitHub; integrate those commits locally before publishing again. Bot commits do not trigger another workflow automatically, so manually run Deploy Static Site afterward if you want them deployed immediately.
- TDEC permit cache files remain ignored. Without an optional refresh, maps use live public services for those permits. Existing committed ECHO caches remain available. Rebuild other datasets locally with the existing data commands before publishing when needed.

References: [GitHub Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages), [Pages availability and limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits), [Next.js static exports](https://nextjs.org/docs/app/guides/static-exports).

## Land use / land cover map layer

County maps offer an off-by-default **Land use / land cover** overlay from [USGS Annual NLCD](https://www.usgs.gov/centers/eros/science/annual-nlcd-data-access), observation year 2025 (Collection 1.2). Hover over the map for the category name, color, explanation and source year. Category explanations appear in the popup instead of the sidebar legend.

The broad groups distinguish built-up land, developed open space, agriculture, forest, grass/shrubland, wetlands, water and barren land. NLCD measures land cover; it does not define zoning or an official urban/rural designation. Cells are nearest-neighbor samples at 300 Web Mercator meters (approximately 240–250 ground meters in Tennessee), so small features may be omitted. County boundaries mask the images, and existing map overlays render above them.

`npm run data:build-landuse` downloads only a Tennessee subset through the [official USGS/MRLC WCS service](https://dmsdata.cr.usgs.gov/geoserver/mrlc_Land-Cover-Native_conus_year_data/wcs) and stores the compressed source raster in ignored `data/raw/`. Later runs reuse that cache; `npm run data:build-landuse -- --download` requests a fresh copy. Dependencies are in `requirements.txt`. The committed, palette-compressed county PNGs and manifest live in `public/data/landuse/` and work on static hosting without a GIS backend. Only the current county image loads when the layer is enabled. Run `npm run build` after regeneration.

## Superfund map layer

County maps include the point layer used by EPA's [Superfund Where You Live map](https://www.epa.gov/superfund/search-superfund-sites-where-you-live): [Superfund NPL Sites with Status Information](https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/Superfund_National_Priorities_List_(NPL)_Sites_with_Status_Information/FeatureServer/0).

The committed Tennessee snapshot is `public/data/layers/superfund-sites.geojson`. County assignment follows EPA's County field, including sites associated with multiple counties. Relevant county maps offer the layer with its toggle off by default, with red current-NPL markers and gray deleted-NPL markers when enabled. Click a marker for its status, EPA ID, dates, and EPA site profile. These are reference locations, not contamination boundaries; an empty county does not establish that it has no contaminated properties.

Refresh the snapshot and county map payloads with `npm run data:refresh-superfund`, then run `npm run build`. The full `npm run data:build` pipeline reapplies the committed snapshot without requiring a live EPA request. Source attribution and retrieval date appear on the Sources page.

## Weekly Dynamic Data Cache

Most datasets remain committed static JSON and GeoJSON under `public/data`. ECHO violation files are also committed because they are small, change infrequently, and keep county maps useful when the EPA ECHO service is unavailable. TDEC permit files remain generated during deployment because they are larger and change more often:

- `public/data/weekly/{county}/tdec-permits.geojson`
- `public/data/weekly/{county}/echo-violations.geojson`
- `public/data/weekly/manifest.json`

County maps load cached files first and fall back to the live public services when a cache file is missing. A failed ECHO refresh leaves the last committed ECHO cache in place.

To test one county locally:

```bash
npm run data:refresh-weekly -- --county davidson --strict
npm run dev
```

To refresh only the committed ECHO cache:

```bash
npm run data:refresh-echo -- --strict
```

## Current Prototype Scope

- Homepage with placeholder Tennessee county map component
- Example county pages:
  - `/counties/davidson`
  - `/counties/williamson`
  - `/counties/cheatham`
  - `/counties/shelby`
- Source metadata page
- Methodology page
- Mock static data contracts in `public/data`

## Data Contracts

- `public/data/counties/index.json`
- `public/data/counties/{slug}.json`
- `public/data/metadata/data-sources.json`
- `public/data/metadata/last-updated.json`
- `public/data/search/search-index.json`
- `public/data/county-maps/{slug}.json`
- `public/data/weekly/{slug}/tdec-permits.geojson` generated during deployment
- `public/data/weekly/{slug}/echo-violations.geojson` committed as the stale-safe ECHO cache

County map utility features include TDEC service-line inventory counts as `total_lines`, `lead_lines`, `non_lead_lines`, `grr_lines`, and `unknown_lines` where TDEC publishes those values for the PWSID.

These contracts are intentionally production-portable. A later pipeline can generate the same outputs from PostGIS and scheduled ETL without forcing major frontend changes.

## Repository Structure

```text
src/app                 App routes
src/components          UI components
src/lib                 File-based data loaders
public/data             Static runtime data contracts
scripts                 ETL placeholders
requirements.txt        Python dependencies for local ETL
data                    Raw / processed / export working directories
content                 Portable editorial content
docs                    Architecture notes
```

## GitHub Pages Notes

- Suitable for the current static prototype
- Not suitable for live backend features
- Keep large future geometries simplified or move them to better static asset hosting if they outgrow GitHub Pages

## TODO

- Replace mock county JSON with real Tennessee county summaries
- Add simplified county and HUC8 geometries
- Build local ETL scripts for ACS, CEJST, legislative districts, and watersheds
- Add source version, fetch date, and refresh frequency to all datasets
- Add accessible layer controls and legends
- Evaluate when tract-level geometry becomes too large for GitHub Pages delivery
- Plan migration to PMTiles/object storage if static assets outgrow repo-friendly delivery
