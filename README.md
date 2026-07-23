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

## GitHub Pages Deployment

- Push this repo to GitHub.
- Set the default branch to `main`.
- In the repository settings, enable `GitHub Pages` with `GitHub Actions` as the source.
- The workflow at `.github/workflows/deploy.yml` refreshes the weekly EPA ECHO and TDEC permit cache, builds the static site, and publishes the contents of `out/`.

## GitHub Workflows

- `.github/workflows/ci.yml` runs `npm run lint` and `npm run build` for pull requests and manual checks.
- `.github/workflows/deploy.yml` runs on pushes to `main`, manual dispatch, and every Monday at `10:17 UTC`.
- The deploy workflow runs `npm run data:refresh-weekly` before `npm run build`, so the published static artifact includes the latest generated TDEC cache and any updated ECHO cache.
- Manual deploys include a `refresh_live_layers` toggle. Leave it on for production deploys; turn it off only when testing build/deploy behavior without external data calls.
- `.github/workflows/refresh-echo-cache.yml` runs every Tuesday at `11:42 UTC` and can be run manually. It refreshes only ECHO, then commits the ECHO cache files when their contents actually change.

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
- `public/data/weekly/{slug}/tdec-permits.geojson` generated during deployment
- `public/data/weekly/{slug}/echo-violations.geojson` committed as the stale-safe ECHO cache

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
