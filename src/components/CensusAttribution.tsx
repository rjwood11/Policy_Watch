export function CensusAttribution() {
  return (
    <aside aria-label="U.S. Census Bureau attribution" className="rounded-lg border border-river/20 bg-foam/80 px-4 py-3 text-sm leading-6 text-ink/80">
      <p>This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau.</p>
      <p className="mt-1 flex flex-wrap gap-x-4">
        <a href="https://www.census.gov/programs-surveys/acs" target="_blank" rel="noreferrer">U.S. Census Bureau · American Community Survey</a>
        <a href="https://www.census.gov/data/developers/about/terms-of-service.html" target="_blank" rel="noreferrer">Census API terms of service</a>
      </p>
    </aside>
  );
}
