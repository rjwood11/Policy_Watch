# Harpeth Conservancy's Water Policy Watch

[Explore Water Policy Watch](https://rjwood11.github.io/Policy_Watch/)

Water Policy Watch helps people explore water quality and environmental conditions across Tennessee's 95 counties. It brings maps, county summaries, and public data together to make local water policy easier to understand.

## What you can do

- Choose a county from the Tennessee map or county directory.
- Explore rivers, water-quality assessments, watersheds, water permits, and compliance records.
- Turn map layers on and off to view drinking-water service areas, protected lands, landfills, Superfund sites, land cover, and legislative districts.
- Read county summaries covering population, poverty, monitoring stations, impaired river miles, and environmental screening indicators.
- Compare counties through statewide rankings and review the Sources and Methodology pages.
- Enable ECHO violations on a county map to read a short explanation of the compliance flags, and use the Glossary for agency, mapping, and permit acronyms. Dotted-underlined acronyms also provide hover definitions.

## How it works

The application combines saved county data with interactive maps. Most summaries and map layers are prepared in advance. Some map information comes from public services when you open a county page; saved copies provide a fallback for certain layers.

The website is hosted on GitHub Pages. Data updates are managed separately, so different datasets can reflect different reporting periods and update dates.

## Automatic data updates

Once this workflow is published, GitHub Actions checks online sources every Saturday at **2:00 a.m. America/Chicago** (Central Time, including daylight saving time). GitHub may delay scheduled runs. The same workflow validates the data, builds the static website, commits generated data, and deploys the updated site; it does not rely on a bot commit triggering another workflow. A normal owner push still deploys saved data without downloading it again.

Weekly checks cover TDEC water permits, EPA ECHO compliance, Superfund, Census county boundaries and the newest published ACS five-year estimates, USGS watersheds and protected areas, legislative districts, drinking-water service areas, service-line inventories, and landfill permits. Census release discovery avoids freezing the app on the 2024 edition. The first Saturday of each month also checks the latest annual NLCD imagery release. ATTAINS and address search query live services when used; their weekly check verifies availability, not a new agency publication date.

The Sources page shows each dataset's last successful refresh, latest check, and refresh status. Local GIS snapshots (including the 2026 impairment layer, Justice40, monitoring stations, scenic rivers, and the separate active-permit summary) require manual replacement and retain their dates. Refreshing the TDEC map cache does not replace the separate local active-permit summary. County boundaries, ACS, watersheds, and districts rebuild as a group. Optional overlay failures retain their previous layers; failed service-line downloads retain existing utility inventory values. A failed core GIS rebuild restores the previous output. Other refresh tasks continue, and incomplete runs are flagged in Actions after available updates deploy.

To refresh locally, run `npm run data:refresh-online` (Python dependencies: `pip install -r requirements.txt`), then `npm run check`. Add `-- --include-landcover` to check imagery immediately. Run `python -m unittest scripts.validate.test_refresh` for failure-handling checks. The Deploy Static Site workflow also supports a manual run with **Refresh online data sources before building** enabled. Repository Actions must allow workflow write access and the bot must be permitted to push generated data to the branch. No scheduled run starts until these local workflow changes reach the default branch.

If Census requires authentication, add an agency-issued API key as the repository Actions secret `CENSUS_API_KEY` (or as a local environment variable). Without it, existing ACS indicators and their dates are retained while other sources can refresh. USGS and other agency outages are also reported without advancing affected refresh dates.

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

The application's [Sources page](https://rjwood11.github.io/Policy_Watch/sources/) describes individual datasets and their update information. The [Methodology page](https://rjwood11.github.io/Policy_Watch/methodology/) explains the general approach.

## Understanding the information

County summaries and rankings offer context for exploration. Rank 1 means the largest value for that measure; its meaning depends on the measure. Saved summaries and live map layers can differ because they use different snapshots or assessment methods. Environmental screening flags describe broader community conditions, and land-cover maps describe surface cover rather than zoning.

Use the source notes and dates when interpreting a result, and follow links to the original records for more detail.
