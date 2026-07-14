import Link from "next/link";
import { notFound } from "next/navigation";
import { CountyDetailMap } from "@/components/CountyDetailMap";
import { IndicatorCard } from "@/components/IndicatorCard";
import type { CountyRecord, StateRank } from "@/lib/data";
import { getCounty, getCountyIndex, getDataSources } from "@/lib/data";

export function generateStaticParams() {
  return getCountyIndex().map((county) => ({ slug: county.slug }));
}

function RankNote({
  rank,
  label = "State rank"
}: {
  rank: StateRank | undefined;
  label?: string;
}) {
  if (!rank) {
    return null;
  }

  return (
    <p className="mt-2 text-xs leading-5 text-river">
      {label}: {rank.display}
    </p>
  );
}

function StressMetric({
  metric
}: {
  metric: CountyRecord["stressSummary"]["water"] | CountyRecord["stressSummary"]["climate"];
}) {
  return (
    <div className="border-t border-ink/10 pt-4 first:border-t-0 first:pt-0">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-ink">{metric.label}</p>
          <p className="mt-1 text-xs leading-5 text-ink/60">
            {metric.tracts} of {metric.tractCount} census tracts
          </p>
        </div>
        <p className="text-2xl font-semibold text-ink">{metric.percent.toFixed(1)}%</p>
      </div>
      <RankNote rank={metric.stateRank} />
      <p className="mt-2 text-sm leading-6 text-ink/75">{metric.description}</p>
    </div>
  );
}

function StressSummaryTile({ county }: { county: CountyRecord }) {
  return (
    <article className="card p-5">
      <p className="text-xs uppercase tracking-normal text-river">cejst-stress</p>
      <h3 className="mt-2 text-lg font-semibold">Water and climate stress</h3>
      <div className="mt-4 space-y-4">
        <StressMetric metric={county.stressSummary.water} />
        <StressMetric metric={county.stressSummary.climate} />
      </div>
      <p className="mt-4 text-xs uppercase tracking-normal text-river">
        {county.stressSummary.sourceDataset} - updated {county.stressSummary.updatedAt}
      </p>
      <p className="mt-4 text-xs leading-5 text-ink/60">Caveat: {county.stressSummary.caveat}</p>
    </article>
  );
}

function CountySnapshotTile({ county }: { county: CountyRecord }) {
  return (
    <article className="card p-7">
      <p className="text-xs uppercase tracking-normal text-river">County snapshot</p>
      <dl className="mt-4 space-y-3 text-sm">
        <div className="flex items-start justify-between gap-4 border-b border-ink/10 pb-3">
          <dt className="font-medium">Population</dt>
          <dd className="text-right">
            <span>{county.population.toLocaleString()}</span>
            <span className="mt-1 block text-xs text-river">
              State rank: {county.rankings.population.display}
            </span>
          </dd>
        </div>
        <div className="flex items-start justify-between gap-4 border-b border-ink/10 pb-3">
          <dt className="font-medium">HUC8 watersheds</dt>
          <dd className="text-right">{county.watersheds.join(", ")}</dd>
        </div>
        <div className="flex items-start justify-between gap-4 border-b border-ink/10 pb-3">
          <dt className="font-medium">Legislative districts</dt>
          <dd className="text-right">{county.legislativeDistricts.join(", ")}</dd>
        </div>
        <div className="flex items-start justify-between gap-4 pb-3">
          <dt className="font-medium">Congressional districts</dt>
          <dd className="text-right">{county.congressionalDistricts.join(", ")}</dd>
        </div>
      </dl>
    </article>
  );
}

function CountyCoverageTile({ county }: { county: CountyRecord }) {
  return (
    <article className="card p-5">
      <p className="text-xs uppercase tracking-normal text-river">County coverage</p>
      <h2 className="mt-2 text-lg font-semibold">
        {county.isFeatured ? "Featured profile" : "Statewide profile"}
      </h2>
      <p className="mt-3 text-xs uppercase tracking-normal text-river">
        Last rebuilt {county.buildDate}
      </p>
      <ul className="mt-4 space-y-2 text-sm leading-6 text-ink/75">
        {county.prototypeStatus.availableFeatures.map((feature) => (
          <li key={feature} className="rounded-md bg-sand px-4 py-3">
            {feature}
          </li>
        ))}
      </ul>
    </article>
  );
}

export default async function CountyPage({
  params
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const countyIndex = getCountyIndex();
  const exists = countyIndex.some((county) => county.slug === slug);

  if (!exists) {
    notFound();
  }

  const county = getCounty(slug);
  const sources = getDataSources();

  return (
    <div className="shell space-y-8 py-10">
      <div className="flex flex-wrap items-center gap-2 text-sm text-ink/70">
        <Link href="/">Home</Link>
        <span>/</span>
        <span>{county.name}</span>
      </div>

      <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">{county.region}</p>
          <h1 className="mt-2 text-4xl font-semibold">{county.name} County</h1>
        </div>
        <CountySnapshotTile county={county} />
      </section>

      <CountyDetailMap name={county.name} slug={county.slug} />

      <section className="grid gap-4 md:grid-cols-3">
        <CountyCoverageTile county={county} />
        {county.indicators.map((indicator) => (
          <IndicatorCard key={indicator.key} indicator={indicator} />
        ))}
        <StressSummaryTile county={county} />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
        <article className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">Impaired waters</p>
          <h2 className="mt-2 text-2xl font-semibold">2026 stream-mile snapshot</h2>
          <p className="mt-4 text-sm leading-7 text-ink/75">{county.impairmentSummary}</p>
          <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
            <div className="rounded-md bg-sand px-4 py-3">
              <dt className="text-ink/60">Impaired stream miles</dt>
              <dd className="mt-1 text-lg font-semibold text-ink">{county.streamMiles.impaired.toFixed(1)}</dd>
              <RankNote rank={county.rankings.impairedRiverMiles} />
            </div>
            <div className="rounded-md bg-sand px-4 py-3">
              <dt className="text-ink/60">Full attainment stream miles</dt>
              <dd className="mt-1 text-lg font-semibold text-ink">
                {county.streamMiles.fullAttainment.toFixed(1)}
              </dd>
              <RankNote rank={county.rankings.fullAttainmentRiverMiles} />
            </div>
            <div className="rounded-md bg-sand px-4 py-3">
              <dt className="text-ink/60">Not currently assessed</dt>
              <dd className="mt-1 text-lg font-semibold text-ink">
                {county.streamMiles.notAssessed.toFixed(1)}
              </dd>
              <RankNote rank={county.rankings.notAssessedRiverMiles} />
            </div>
            <div className="rounded-md bg-sand px-4 py-3">
              <dt className="text-ink/60">Other assessed categories</dt>
              <dd className="mt-1 text-lg font-semibold text-ink">
                {county.streamMiles.otherAssessed.toFixed(1)}
              </dd>
              <RankNote rank={county.rankings.otherAssessedRiverMiles} />
            </div>
          </dl>
          <div className="mt-5">
            <h3 className="text-sm font-semibold text-ink">All local attainment categories currently present</h3>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-ink/75">
              {county.attainmentCategories.map((entry) => (
                <li key={entry.category} className="flex items-start justify-between gap-4 rounded-md border border-ink/10 px-4 py-3">
                  <span>{entry.label}</span>
                  <span className="font-medium text-ink">{entry.miles.toFixed(1)} mi</span>
                </li>
              ))}
            </ul>
          </div>
          {county.impairmentCauses?.length > 0 ? (
            <div className="mt-5">
              <h3 className="text-sm font-semibold text-ink">Leading impairment causes</h3>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-ink/75">
                {county.impairmentCauses.map((entry) => (
                  <li key={entry.cause} className="flex items-start justify-between gap-4 rounded-md border border-ink/10 px-4 py-3">
                    <span>{entry.label}</span>
                    <span className="text-right font-medium text-ink">
                      {entry.miles.toFixed(1)} mi
                      <span className="block text-xs font-normal text-ink/60">
                        {entry.assessmentUnits} assessment unit{entry.assessmentUnits === 1 ? "" : "s"}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <p className="mt-4 text-xs leading-6 text-ink/60">
            These river-mile values come from the local 2026 impairment layer intersected with
            county boundaries. Shared waters can contribute to more than one county summary.
          </p>
          {county.sampleImpairments?.length > 0 ? (
            <div className="mt-5">
              <h3 className="text-sm font-semibold text-ink">Example impaired streams</h3>
              <ul className="mt-3 space-y-2 text-sm leading-7 text-ink/75">
                {county.sampleImpairments.map((entry) => (
                  <li key={`${entry.waterbody}-${entry.status}`} className="rounded-md bg-sand px-4 py-3">
                    <span className="block font-medium text-ink">{entry.waterbody}</span>
                    <span className="mt-1 block text-xs leading-5 text-ink/65">
                      {entry.causes.length > 0 ? entry.causes.join(", ") : "Cause not specified"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : county.sampleWaterbodies.length > 0 ? (
            <ul className="mt-4 space-y-2 text-sm leading-7 text-ink/75">
              {county.sampleWaterbodies.map((waterbody) => (
                <li key={waterbody} className="rounded-md bg-sand px-4 py-3">
                  {waterbody}
                </li>
              ))}
            </ul>
          ) : null}
        </article>
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <article className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">Monitoring</p>
          <h2 className="mt-2 text-2xl font-semibold">Station context</h2>
          <p className="mt-4 text-sm leading-7 text-ink/75">
            {county.monitoringSummary.stations} monitoring stations are associated with{" "}
            {county.name} County, including {county.monitoringSummary.riverStations} river or stream
            stations in the local DWR layer.
          </p>
          <RankNote rank={county.rankings.monitoringStations} />
        </article>
        <article className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">Permits</p>
          <h2 className="mt-2 text-2xl font-semibold">Water permit context</h2>
          <p className="mt-4 text-sm leading-7 text-ink/75">
            The local permitted-features layer shows {county.permittingSummary.activePermits} active
            permitted features and {county.permittingSummary.uniquePermittees} distinct permittees in
            this county.
          </p>
          <RankNote rank={county.rankings.activePermits} />
        </article>
        <article className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">Scenic and service areas</p>
          <h2 className="mt-2 text-2xl font-semibold">Additional local context</h2>
          <p className="mt-4 text-sm leading-7 text-ink/75">
            {county.scenicRiverSummary.miles.toFixed(1)} scenic river miles and{" "}
            {county.waterServiceSummary.serviceAreas} overlapping public water service areas are
            currently summarized for {county.name} County.
          </p>
          <RankNote label="Scenic river rank" rank={county.rankings.scenicRiverMiles} />
          <RankNote label="Water service rank" rank={county.rankings.waterServiceAreas} />
        </article>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
        <article className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">Justice40 / CEJST</p>
          <h2 className="mt-2 text-2xl font-semibold">Screening summary</h2>
          <p className="mt-4 text-sm leading-7 text-ink/75">{county.cejstSummary}</p>
          <p className="mt-4 text-xs leading-6 text-ink/60">
            Screening tools are contextual. They are not a final determination of risk,
            regulatory status, or community need.
          </p>
        </article>
        <article className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">Get involved locally</p>
          <h2 className="mt-2 text-2xl font-semibold">
            {county.isFeatured ? "Featured civic action prompts" : "County-level action prompts"}
          </h2>
          <ul className="mt-4 space-y-3 text-sm leading-7 text-ink/75">
            {county.getInvolved.map((item) => (
              <li key={item} className="rounded-md bg-sand px-4 py-3">
                {item}
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="card p-7">
        <p className="text-xs uppercase tracking-normal text-river">Data sources</p>
        <h2 className="mt-2 text-2xl font-semibold">Source notes</h2>
        <p className="mt-3 text-sm leading-7 text-ink/75">
          Each indicator card includes its dataset label and the current rebuild date. The full
          registry is available on the sources page.
        </p>
        <ul className="mt-5 space-y-4 text-sm leading-7 text-ink/75">
          {sources.slice(0, 6).map((source) => (
            <li key={source.dataset} className="rounded-md border border-ink/10 p-4">
              <span className="font-medium text-ink">{source.dataset}:</span> {source.notes}
            </li>
          ))}
        </ul>
        <Link href="/sources" className="mt-5 inline-block text-sm">
          Review the full source registry
        </Link>
      </section>
    </div>
  );
}
