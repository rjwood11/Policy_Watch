# TDEC feed access from GitHub

The complete water-permit and landfill-permit feeds remain:

- Water: `https://tdeconline.tn.gov/arcgis/rest/services/DWR_Public/MapServer/1`
- Landfills: `https://tdeconline.tn.gov/arcgis/rest/services/SWM_Permits/MapServer/0`

On November 11, 2026, public metadata and count queries returned HTTP 403 from
GitHub-hosted Linux, Windows, and macOS runners. Both GET and POST queries failed,
including requests using the same browser headers that worked on the owner's
computer. These tests establish an access difference; they do not establish
which agency firewall rule caused it.

Evidence: [Linux and Windows check](https://github.com/rjwood11/Policy_Watch/actions/runs/43087176339)
and [macOS check](https://github.com/rjwood11/Policy_Watch/actions/runs/43087502553).
The Actions workflow **Check public TDEC access** can retest the complete feeds
without running an entire data refresh or changing any saved data. A failed
check must remain a failure, even when previous permit caches are available.

## Coverage decision

TDEC's [current water viewer](https://experience.arcgis.com/experience/bab9713d62d64d21944420e604980244)
still references the same water-permit service. Its
[official Hub item](https://tdec-division-of-water-tdec.hub.arcgis.com/datasets/248adb0d83af4d0fa943d9b1b4ca1c7b_1/about)
did not provide a working GeoJSON download during this investigation.

The newer [Permitted Tennessee Landfills service](https://maps.tdec.tn.gov/hosting/rest/services/Permitted_Tennessee_Landfills/FeatureServer/0)
was accessible from all three GitHub platforms, but returned only 111 facility
records and lacks permit numbers, permit actions, and permit dates. It is not
an equivalent replacement for the existing detailed landfill-permit layer.
The owner explicitly chose to preserve the existing full permit coverage.

## Restoring unattended refreshes

The owner chose a weekly **local** water-permit refresh, Fridays at **9 AM
America/Chicago**, followed by validation, a scoped data commit, and a push to
GitHub. A Codex scheduled task performs this work on the owner's computer;
the computer and app must be running. Source downloads and before/after versions
are preserved in the ignored local `data/archives/` directory. Only the refreshed
public caches and metadata are committed. The task stops if the checkout contains
unrelated changes, the downloads fail, or validation fails.

GitHub-hosted full refreshes now run the weekly ECHO source only, preserving
the locally published TDEC water cache and its success status/date. Local full
refreshes still attempt both sources. This policy applies to the weekly water
permit cache; the separate landfill and survey permit-detail feeds keep their
existing refresh behavior.

To run the water refresh manually from the project directory:

```powershell
python -u -m scripts.refresh.weekly_layers --source tdec --strict
python -m scripts.validate.validate_prototype_outputs
npm run check
```

After successful checks, use `PUBLISH-TO-GITHUB.bat` to publish deliberate local
changes. The scheduled task commits only its TDEC water data and metadata.

### Future direct GitHub access

TDEC must provide an approved public endpoint or bulk download with equivalent
records and fields, or permit access from a GitHub refresh runner. This repository
does not route requests through third-party proxies or install a local runner.
Ask the agency which access method it supports for a weekly public-data refresh;
do not assume a particular firewall or IP allowlist is the solution.

After access is restored, run **Check public TDEC access**, then manually run
**Deploy Static Site** with **Refresh online data sources before building** enabled.
Verify all 95 water-permit county refreshes and the landfill source succeed,
verify the source archive, and download its artifact for permanent local storage.
The existing unattended refresh workflow will use the same feeds on future runs.

Until then, the refresh keeps the complete previously saved permit layers and
successful-refresh dates, reports the access failure, and continues other sources.
Water-permit access is checked once before county requests, avoiding 95 repeated
attempts against a service that rejected the shared access check. HTTP 403
responses fail immediately; temporary server errors retain their retry behavior.
