import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CountyDetailMap } from "@/components/CountyDetailMap";
import type { CountyRecord, StateRank } from "@/lib/data";
import { getCounty, getCountyIndex, getDataSources } from "@/lib/data";

const TN_WATER_WATCH_COUNTIES = new Set(["davidson", "williamson"]);
const TN_WATER_WATCH_URL = "https://tnwaterwatch.org/";

type IndicatorRecord = CountyRecord["indicators"][number];

export function generateStaticParams() {
  return getCountyIndex().map((county) => ({ slug: county.slug }));
}

export async function generateMetadata({
  params
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const county = getCountyIndex().find((entry) => entry.slug === slug);

  if (!county) {
    return {
      title: "County Not Found"
    };
  }

  return {
    title: `${county.name} County | Harpeth Conservancy's Water Policy Watch`,
    description: `${countyRegionSubtitle(county)} Water quality, permitting, and policy context from Harpeth Conservancy.`
  };
}

function countyRegionSubtitle(county: Pick<CountyRecord, "name" | "region">) {
  return `${county.name} County is in ${county.region}.`;
}

function findIndicator(county: CountyRecord, key: string) {
  return county.indicators.find((indicator) => indicator.key === key);
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

function StatBlock({
  label,
  value,
  detail,
  rank
}: {
  label: string;
  value: string;
  detail?: string;
  rank?: StateRank;
}) {
  return (
    <div className="rounded-md bg-sand px-4 py-3">
      <dt className="text-sm text-ink/60">{label}</dt>
      <dd className="mt-1 text-xl font-semibold text-ink">{value}</dd>
      <RankNote rank={rank} />
      {detail ? <p className="mt-2 text-xs leading-5 text-ink/60">{detail}</p> : null}
    </div>
  );
}

function IndicatorDefinition({ indicator }: { indicator: IndicatorRecord | undefined }) {
  if (!indicator) {
    return null;
  }

  return (
    <p className="mt-2 text-xs leading-5 text-ink/60">
      {indicator.definition} Caveat: {indicator.caveat}
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
    <article className="card p-6">
      <p className="text-xs uppercase tracking-normal text-river">Climate and water stress</p>
      <h3 className="mt-2 text-xl font-semibold">Justice40 / CEJST tract screening</h3>
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

function CountyContextTile({ county }: { county: CountyRecord }) {
  return (
    <article className="card p-6">
      <p className="text-xs uppercase tracking-normal text-river">County context</p>
      <dl className="mt-4 space-y-3 text-sm">
        <div className="border-b border-ink/10 pb-3">
          <dt className="font-medium text-ink">HUC8 watersheds</dt>
          <dd className="mt-1 text-ink/70">{county.watersheds.join(", ")}</dd>
        </div>
        <div className="border-b border-ink/10 pb-3">
          <dt className="font-medium text-ink">Legislative districts</dt>
          <dd className="mt-1 text-ink/70">{county.legislativeDistricts.join(", ")}</dd>
        </div>
        <div>
          <dt className="font-medium text-ink">Congressional districts</dt>
          <dd className="mt-1 text-ink/70">{county.congressionalDistricts.join(", ")}</dd>
        </div>
      </dl>
      <p className="mt-4 text-xs uppercase tracking-normal text-river">Last rebuilt {county.buildDate}</p>
    </article>
  );
}

function SectionJumpNav() {
  const sections = [
    { href: "#county-map", label: "Map" },
    { href: "#rivers", label: "Rivers" },
    { href: "#population", label: "Population" },
    { href: "#permits", label: "Permits" },
    { href: "#climate", label: "Climate" }
  ];

  return (
    <nav className="card flex flex-wrap gap-2 p-3" aria-label="County page sections">
      {sections.map((section) => (
        <Link
          key={section.href}
          href={section.href}
          className="rounded-md border border-ink/10 bg-sand px-4 py-2 text-sm font-medium text-ink no-underline transition hover:border-gold/45 hover:bg-white"
        >
          {section.label}
        </Link>
      ))}
    </nav>
  );
}

function TennesseeWaterWatchCard({ county }: { county: CountyRecord }) {
  if (!TN_WATER_WATCH_COUNTIES.has(county.slug)) {
    return null;
  }

  return (
    <div className="rounded-md border border-river/20 bg-mist/70 px-4 py-3">
      <p className="text-sm font-semibold text-ink">TN Water Watch river advisories</p>
      <p className="mt-2 text-sm leading-6 text-ink/70">
        Forecasted E. coli advisories are available for Middle Tennessee recreation access
        points, including Harpeth-area locations relevant to this county.
      </p>
      <a href={TN_WATER_WATCH_URL} target="_blank" rel="noreferrer" className="mt-3 inline-block text-sm font-medium">
        Open TN Water Watch
      </a>
    </div>
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
  const echoSource = sources.find((source) => source.dataset === "EPA ECHO CWA permit compliance");
  const populationIndicator = findIndicator(county, "acs-pop");
  const povertyIndicator = findIndicator(county, "acs-poverty");
  const disadvantagedIndicator = findIndicator(county, "j40-disadvantaged");
  const impairedIndicator = findIndicator(county, "impaired-river-miles");
  const monitoringIndicator = findIndicator(county, "monitoring-stations");
  const activePermitsIndicator = findIndicator(county, "active-permits");
  const scenicIndicator = findIndicator(county, "scenic-river-miles");

  return (
    <div className="shell space-y-8 py-10">
      <div className="flex flex-wrap items-center gap-2 text-sm text-ink/70">
        <Link href="/">Home</Link>
        <span>/</span>
        <span>{county.name}</span>
      </div>

      <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="card border-river/30 bg-white p-7 text-black md:p-9">
          <h1 className="text-5xl font-bold leading-tight tracking-normal text-black sm:text-6xl lg:text-7xl">
            {county.name} County
          </h1>
          <p className="mt-4 text-xl font-semibold text-river">
            {countyRegionSubtitle(county)}
          </p>
          <p className="mt-5 max-w-3xl text-sm leading-7 text-ink/75">{county.overview}</p>
        </div>
        <CountyContextTile county={county} />
      </section>

      <SectionJumpNav />

      <CountyDetailMap echoUpdatedAt={echoSource?.lastUpdated} name={county.name} slug={county.slug} />

      <section id="rivers" className="grid scroll-mt-6 gap-6 lg:grid-cols-[1fr_0.85fr]">
        <article className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">Rivers</p>
          <h2 className="mt-2 text-2xl font-semibold">Impaired waters and monitoring</h2>
          <p className="mt-4 text-sm leading-7 text-ink/75">{county.impairmentSummary}</p>
          <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
            <StatBlock
              label="Impaired river miles"
              value={`${county.streamMiles.impaired.toFixed(1)} mi`}
              detail={impairedIndicator?.definition}
              rank={county.rankings.impairedRiverMiles}
            />
            <StatBlock
              label="Monitoring stations"
              value={county.monitoringSummary.stations.toLocaleString()}
              detail={`${county.monitoringSummary.riverStations.toLocaleString()} are river or stream stations in the local DWR layer. ${monitoringIndicator?.definition ?? ""}`}
              rank={county.rankings.monitoringStations}
            />
            <StatBlock
              label="Full attainment river miles"
              value={`${county.streamMiles.fullAttainment.toFixed(1)} mi`}
              detail="Assessed local stream miles currently summarized as full attainment."
              rank={county.rankings.fullAttainmentRiverMiles}
            />
            <StatBlock
              label="Not currently assessed"
              value={`${county.streamMiles.notAssessed.toFixed(1)} mi`}
              detail="Mapped stream miles in this county that do not currently carry an assessment status."
              rank={county.rankings.notAssessedRiverMiles}
            />
            <StatBlock
              label="Scenic river miles"
              value={`${county.scenicRiverSummary.miles.toFixed(1)} mi`}
              detail={
                county.scenicRiverSummary.segments > 0
                  ? `${county.scenicRiverSummary.segments} scenic segment summary record${
                      county.scenicRiverSummary.segments === 1 ? "" : "s"
                    }.`
                  : scenicIndicator?.definition
              }
              rank={county.rankings.scenicRiverMiles}
            />
          </dl>

          <div className="mt-5">
            <h3 className="text-sm font-semibold text-ink">Local attainment categories</h3>
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
            River-mile values come from the local 2026 impairment layer intersected with county
            boundaries. Shared waters can contribute to more than one county summary.
          </p>
        </article>

        <aside className="space-y-6">
          <article className="card p-6">
            <p className="text-xs uppercase tracking-normal text-river">Example streams</p>
            <h3 className="mt-2 text-xl font-semibold">Local waterbody context</h3>
            {county.sampleImpairments?.length > 0 ? (
              <ul className="mt-4 space-y-2 text-sm leading-7 text-ink/75">
                {county.sampleImpairments.map((entry) => (
                  <li key={`${entry.waterbody}-${entry.status}`} className="rounded-md bg-sand px-4 py-3">
                    <span className="block font-medium text-ink">{entry.waterbody}</span>
                    <span className="mt-1 block text-xs leading-5 text-ink/65">
                      {entry.causes.length > 0 ? entry.causes.join(", ") : "Cause not specified"}
                    </span>
                  </li>
                ))}
              </ul>
            ) : county.sampleWaterbodies.length > 0 ? (
              <ul className="mt-4 space-y-2 text-sm leading-7 text-ink/75">
                {county.sampleWaterbodies.map((waterbody) => (
                  <li key={waterbody} className="rounded-md bg-sand px-4 py-3">
                    {waterbody}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm leading-6 text-ink/70">No local example streams are listed in this snapshot.</p>
            )}
          </article>
        </aside>
      </section>

      <section id="population" className="grid scroll-mt-6 gap-6 lg:grid-cols-[0.9fr_1fr]">
        <article className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">Population</p>
          <h2 className="mt-2 text-2xl font-semibold">People and screening context</h2>
          <div className="mt-5 rounded-md bg-sand p-4">
            <dl className="grid gap-4 sm:grid-cols-2">
              <div>
                <dt className="text-sm text-ink/60">Population</dt>
                <dd className="mt-1 text-2xl font-semibold text-ink">
                  {populationIndicator?.value ?? county.population.toLocaleString()}
                </dd>
                <RankNote rank={county.rankings.population} />
              </div>
              <div>
                <dt className="text-sm text-ink/60">Poverty rate</dt>
                <dd className="mt-1 text-2xl font-semibold text-ink">{povertyIndicator?.value ?? "n/a"}</dd>
                <RankNote rank={povertyIndicator?.stateRank} />
              </div>
            </dl>
            <IndicatorDefinition indicator={populationIndicator} />
            <IndicatorDefinition indicator={povertyIndicator} />
          </div>

          <div className="mt-4 rounded-md border border-ink/10 px-4 py-3">
            <p className="text-sm font-semibold text-ink">Disadvantaged tracts</p>
            <p className="mt-1 text-2xl font-semibold text-ink">{disadvantagedIndicator?.value ?? "n/a"}</p>
            <IndicatorDefinition indicator={disadvantagedIndicator} />
          </div>
        </article>

        <article className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">Justice40 / CEJST</p>
          <h2 className="mt-2 text-2xl font-semibold">Screening summary</h2>
          <p className="mt-4 text-sm leading-7 text-ink/75">{county.cejstSummary}</p>
          <p className="mt-4 text-xs leading-6 text-ink/60">
            Screening tools are contextual. They are not a final determination of risk,
            regulatory status, or community need.
          </p>
        </article>
      </section>

      <section id="permits" className="grid scroll-mt-6 gap-6 lg:grid-cols-[1fr_0.9fr]">
        <article className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">Permits</p>
          <h2 className="mt-2 text-2xl font-semibold">Water permit and service-area context</h2>
          <p className="mt-4 text-sm leading-7 text-ink/75">
            The local permitted-features layer shows {county.permittingSummary.activePermits.toLocaleString()} active
            permitted features and {county.permittingSummary.uniquePermittees.toLocaleString()} distinct permittees in
            this county.
          </p>
          <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
            <StatBlock
              label="Active water permits"
              value={county.permittingSummary.activePermits.toLocaleString()}
              detail={activePermitsIndicator?.definition}
              rank={county.rankings.activePermits}
            />
            <StatBlock
              label="Unique permittees"
              value={county.permittingSummary.uniquePermittees.toLocaleString()}
              detail="Distinct permittee names represented in active local permit features."
            />
            <StatBlock
              label="Public water service areas"
              value={county.waterServiceSummary.serviceAreas.toLocaleString()}
              detail={
                county.waterServiceSummary.names.length > 0
                  ? county.waterServiceSummary.names.slice(0, 4).join("; ")
                  : "No service-area names are listed in this snapshot."
              }
              rank={county.rankings.waterServiceAreas}
            />
          </dl>
        </article>

        <article className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">Get involved locally</p>
          <h2 className="mt-2 text-2xl font-semibold">Local action prompts</h2>
          <ul className="mt-4 space-y-3 text-sm leading-7 text-ink/75">
            {county.getInvolved.map((item) => (
              <li key={item} className="rounded-md bg-sand px-4 py-3">
                {item}
              </li>
            ))}
          </ul>
          <div className="mt-4">
            <TennesseeWaterWatchCard county={county} />
          </div>
        </article>
      </section>

      <section id="climate" className="grid scroll-mt-6 gap-6 lg:grid-cols-[0.9fr_1fr]">
        <StressSummaryTile county={county} />
        <article className="card p-7">
          <p className="text-xs uppercase tracking-normal text-river">Climate</p>
          <h2 className="mt-2 text-2xl font-semibold">How to read this section</h2>
          <p className="mt-4 text-sm leading-7 text-ink/75">
            These tract percentages summarize screening indicators used for environmental justice
            context. They help compare local vulnerability with water and policy signals, but they
            should be read alongside local monitoring and permit records.
          </p>
          <p className="mt-4 text-xs uppercase tracking-normal text-river">
            {county.stressSummary.sourceDataset} - updated {county.stressSummary.updatedAt}
          </p>
        </article>
      </section>

      <section className="card p-7">
        <p className="text-xs uppercase tracking-normal text-river">Data sources</p>
        <h2 className="mt-2 text-2xl font-semibold">Source notes</h2>
        <p className="mt-3 text-sm leading-7 text-ink/75">
          Each county summary is rebuilt from public source files and locally generated county
          overlays. The full registry is available on the sources page.
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
