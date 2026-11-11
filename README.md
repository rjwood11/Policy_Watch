# Harpeth Conservancy's Water Policy Watch

[Explore Water Policy Watch](https://rjwood11.github.io/Policy_Watch/)

Water Policy Watch helps people explore water quality and environmental conditions across Tennessee's 95 counties. It brings maps, county summaries, and public data together to make local water policy easier to understand.

## What you can do

- Choose a county from the Tennessee map or county directory.
- Explore rivers, water-quality assessments, watersheds, water permits, and compliance records.
- Turn map layers on and off to view drinking-water service areas, protected lands, landfills, Superfund sites, land cover, and legislative districts.
- Read county summaries covering population, poverty, monitoring stations, impaired river miles, and environmental screening indicators.
- Compare counties through statewide rankings and review the Sources page.
- Enable ECHO violations on a county map to read a short explanation of the compliance flags, and use the Glossary for agency, mapping, and permit acronyms. Dotted-underlined acronyms also provide hover definitions.

## How it works

The application combines saved county data with interactive maps. Most summaries and map layers are prepared in advance. Some map information comes from public services when you open a county page; saved copies provide a fallback for certain layers.

The website is hosted on GitHub Pages. Data updates are managed separately, so different datasets can reflect different reporting periods and update dates.

## Automatic data updates

Once this workflow is published, GitHub Actions checks online sources every Saturday at **2:00 a.m. America/Chicago** (Central Time, including daylight saving time). GitHub may delay scheduled runs. The same workflow validates the data, builds the static website, commits generated data, and deploys the updated site; it does not rely on a bot commit triggering another workflow. A normal owner push still deploys saved data without downloading it again.

Weekly checks cover TDEC water permits, EPA ECHO compliance, Superfund, Census county boundaries and the newest published ACS five-year estimates, USGS watersheds and protected areas, legislative districts, drinking-water service areas, service-line inventories, and landfill permits. Census release discovery avoids freezing the app on the 2024 edition. The first Saturday of each month also checks the latest annual NLCD imagery release. ATTAINS and address search query live services when used. Weekly refreshes also save the Tennessee ATTAINS dataset and verify address-locator availability; these checks do not establish a new agency publication date.

The Sources page shows each dataset's last successful refresh, latest check, and refresh status. Local GIS snapshots (including the 2026 impairment layer, Justice40, monitoring stations, scenic rivers, and the separate active-permit summary) require manual replacement and retain their dates. Refreshing the TDEC map cache does not replace the separate local active-permit summary. County boundaries, ACS, watersheds, and districts rebuild as a group. Optional overlay failures retain their previous layers; failed service-line downloads retain existing utility inventory values. A failed core GIS rebuild restores the previous output. Other refresh tasks continue, and incomplete runs are flagged in Actions after available updates deploy.

To refresh locally, run `npm run data:refresh-online` (Python dependencies: `pip install -r requirements.txt`), then `npm run check`. Add `-- --include-landcover` to check imagery immediately. Run `python -m unittest scripts.validate.test_refresh` for failure-handling checks. The Deploy Static Site workflow also supports a manual run with **Refresh online data sources before building** enabled. Repository Actions must allow workflow write access and the bot must be permitted to push generated data to the branch. No scheduled run starts until these local workflow changes reach the default branch.

If Census requires authentication, add an agency-issued API key as the repository Actions secret `CENSUS_API_KEY` (or as a local environment variable). Without it, existing ACS indicators and their dates are retained while other sources can refresh. USGS and other agency outages are also reported without advancing affected refresh dates.

For local Census updates, set `CENSUS_API_KEY` in the ignored `.env.local` file (see `.env.example`) and run `npm run data:refresh-census`, then `npm run check`. Python refreshes use the process environment first, then `.env.local`; keys are never written into generated datasets or browser code. This command discovers the newest published ACS five-year release, updates all 95 county population and poverty indicators and their rankings, and retains other map layers. County geography was refreshed separately from Census TIGER/Line. Publishing local files does not configure the GitHub Actions secret; add `CENSUS_API_KEY` in the repository's Actions secrets for hosted refreshes.

The application prominently displays the Census Bureau's required notice in its site footer and on the Sources page: “This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau.” Agency links, source vintages, and the poverty-rate calculation accompany the Census source record. See the [Census API Terms of Service](https://www.census.gov/data/developers/about/terms-of-service.html).

### Local backups after every data refresh

All data refresh/build commands now save versioned before/after snapshots and original validated downloads in `data/archives/`. This includes local GIS inputs and shapefile companion files, the generated county layers, original Census/agency responses, ECHO/TDEC records, and the land-cover raster subset. The online refresh also saves the Tennessee ATTAINS dataset. Identical files share storage; old local versions are not automatically deleted. Archives stay out of Git and the website, and request metadata excludes API keys.

Use `npm run data:archive-list` to inspect history, `npm run data:archive-verify` to check integrity, and `npm run data:archive` for an extra manual snapshot. Recovery goes into a new directory so it cannot overwrite the working app. Hosted refreshes upload separate downloadable backups configured for 90 days; download/import those artifacts to keep them permanently on this computer. Address geocoding indexes, global basemap tiles, and remote fonts are not exportable environmental datasets and are not mirrored. See [backup coverage and recovery instructions](docs/data-backups.md).

To investigate a failed refresh, read `public/data/metadata/refresh-run.json` for the run's errors and `public/data/weekly/manifest.json` for county-level TDEC/ECHO errors. A TDEC HTTP 403 means the service rejected the download; the last good permit and landfill layers are retained. Optional landfill failures must not block the county/watershed rebuild. Land-cover downloads use USGS WCS 1.0 with an explicit observation year because this coverage's WCS 2.0 download returns a server-side `startTime` error; release discovery still uses WCS 2.0 metadata. A successful website build only validates the saved data and application; it does not prove upstream services refreshed successfully.

### Districts and the November 2026 election

District maps use TNMap's state House/Senate boundaries and the Comptroller's May 2026 congressional plan. Run `npm run data:refresh-districts` to update district geometry and county district lists together without rebuilding environmental data. The full online refresh uses the same congressional download. Boundaries are simplified for display; county lists omit intersections below 0.5% of county area.

Member names are maintained separately in `src/lib/tennesseeLegislators.ts`. The November 11, 2026 review incorporated the official 115th General Assembly directories, including 21 changed state House members and one changed senator. Congressional names show reported November 2026 winners, with four changed members, and are explicitly labeled unofficial pending certification; the incoming congressional term begins January 3, 2027. Results were checked against Tennessee Firefly's reporting of Secretary of State returns because the state election endpoint returned HTTP 403. Continuing state senators remain listed, including Brent Taylor until a verified successor is available. Sources and all 26 name changes are recorded in `public/data/metadata/legislative-update.json`. Review certification, vacancies, and member profiles before promoting these results to a current-officeholder roster.

## Where the data comes from

| Source | General contribution |
| --- | --- |
| U.S. Census Bureau | County boundaries, population, and socioeconomic estimates from the American Community Survey. |
| Tennessee Department of Environment and Conservation (TDEC) | Water assessments, permits, monitoring, drinking-water service areas, service-line inventories, and landfill records. |
| U.S. Environmental Protection Agency (EPA) | Water-quality assessment maps, Clean Water Act compliance information through ECHO, and Superfund site records. |
| U.S. Geological Survey (USGS) | Watershed boundaries, protected-area information, and Annual National Land Cover Database imagery. |
| Tennessee's TNMap services | Legislative district boundaries and address searches. |
| Harpeth Conservancy GIS collections | Local copies of Tennessee environmental and geographic datasets, including Justice40 / CEJST screening information. |
| OpenStreetMap | Background maps and road context. |

The application's [Sources page](https://rjwood11.github.io/Policy_Watch/sources/) describes individual datasets and their update information.

## Publishing local changes

Double-click `PUBLISH-TO-GITHUB.bat` (the underscore alias `PUBLISH_TO_GITHUB.bat` also works). It validates the local build and saved data, commits non-ignored changes, safely merges non-conflicting upstream commits, rechecks an integrated version, and pushes `main`. If remote edits conflict, it cancels the merge and keeps your work committed locally for Codex to reconcile; it never force-pushes. The full diagnostic log is saved in `.codex-local/publish-github.log`. Use `PUBLISH-TO-GITHUB.bat -CheckOnly` to validate without committing or pushing.

## Understanding the information

County summaries and rankings offer context for exploration. Rank 1 means the largest value for that measure; its meaning depends on the measure. Saved summaries and live map layers can differ because they use different snapshots or assessment methods. Environmental screening flags describe broader community conditions, and land-cover maps describe surface cover rather than zoning.

Use the source notes and dates when interpreting a result, and follow links to the original records for more detail.
