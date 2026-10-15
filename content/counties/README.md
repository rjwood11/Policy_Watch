# County introductions

`introductions.json` contains an original two-sentence introduction for each of
Tennessee's 95 counties, researched from the linked county Wikipedia article on
October 15, 2026. Each entry includes its source URL, which appears below the
introduction on the county page.

Keep these introductions focused on distinctive local geography, history,
communities, and landmarks. Avoid statistics that would duplicate the refreshed
county indicators or quickly become outdated.

The county page and its search metadata read this editorial file directly through
`src/lib/countyIntroductions.ts`. Data refreshes do not overwrite it. Keep the keys
aligned with `public/data/counties/index.json`; a missing introduction fails the
static build instead of silently restoring generic text.
