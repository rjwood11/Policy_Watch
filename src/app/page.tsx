import Link from "next/link";
import { TennesseeMap } from "@/components/TennesseeMap";
import type { CountyRecord, DataSourceRecord } from "@/lib/data";
import { getCounty, getCountyIndex, getDataSources, getLastUpdated } from "@/lib/data";

const numberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0
});

const primarySourceOrder = [
  "Tennessee counties",
  "HUC8 watersheds",
  "ACS indicators",
  "Justice40 / CEJST local snapshot",
  "2026 303(d) impairment layer",
  "EPA ATTAINS assessment geospatial layer",
  "TDEC DWR public water resources permits",
  "EPA ECHO CWA permit compliance"
];

function formatNumber(value: number) {
  return numberFormatter.format(Math.round(value));
}

function getLatestRefresh(lastUpdated: Record<string, string>) {
  const dates = Object.values(lastUpdated).sort();
  return dates[dates.length - 1] ?? "n/a";
}

function getPrimarySources(sources: DataSourceRecord[]) {
  const byDataset = new Map(sources.map((source) => [source.dataset, source]));
  return primarySourceOrder
    .map((dataset) => byDataset.get(dataset))
    .filter((source): source is DataSourceRecord => Boolean(source));
}

function MetricCard({
  label,
  value,
  detail
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <article className="rounded-lg border border-ink/10 bg-mist/65 p-3">
      <p className="text-xs font-semibold uppercase tracking-normal text-river">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
      <p className="mt-1 text-sm text-ink/60">{detail}</p>
    </article>
  );
}

function SourceTile({ source }: { source: DataSourceRecord }) {
  const isExternal = source.sourceUrl.startsWith("http");

  return (
    <article className="border-t border-ink/10 py-2 first:border-t-0 first:pt-0">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">{source.dataset}</h3>
          <p className="mt-0.5 text-xs leading-4 text-ink/60">{source.sourceName}</p>
        </div>
        <span className="shrink-0 text-xs font-medium text-river">{source.lastUpdated}</span>
      </div>
      <div className="mt-1 flex items-center justify-between gap-3 text-xs text-ink/55">
        <span>{source.refreshFrequency}</span>
        {isExternal ? (
          <a href={source.sourceUrl} target="_blank" rel="noreferrer">
            Open
          </a>
        ) : (
          <span>Local snapshot</span>
        )}
      </div>
    </article>
  );
}

function FeaturedCountyCard({ county }: { county: CountyRecord }) {
  return (
    <Link href={`/counties/${county.slug}`} className="card p-4 no-underline">
      <p className="text-xs font-semibold uppercase tracking-normal text-river">{county.region}</p>
      <h3 className="mt-2 text-xl font-semibold text-ink">{county.name} County</h3>
      <dl className="mt-3 grid gap-2 text-sm">
        <div className="flex items-center justify-between border-t border-ink/10 pt-3">
          <dt className="text-ink/60">Impaired miles</dt>
          <dd className="font-semibold text-ink">{county.streamMiles.impaired.toFixed(1)}</dd>
        </div>
        <div className="flex items-center justify-between border-t border-ink/10 pt-3">
          <dt className="text-ink/60">Active permits</dt>
          <dd className="font-semibold text-ink">{county.permittingSummary.activePermits}</dd>
        </div>
        <div className="flex items-center justify-between border-t border-ink/10 pt-3">
          <dt className="text-ink/60">Monitoring stations</dt>
          <dd className="font-semibold text-ink">{county.monitoringSummary.stations}</dd>
        </div>
      </dl>
    </Link>
  );
}

export default function HomePage() {
  const counties = getCountyIndex();
  const countyDetails = counties.map((county) => getCounty(county.slug));
  const sources = getDataSources();
  const lastUpdated = getLastUpdated();
  const latestRefresh = getLatestRefresh(lastUpdated);
  const statewideCount = counties.filter((county) => county.hasPage).length;
  const featuredCountyDetails = countyDetails.filter((county) => county.isFeatured);
  const primarySources = getPrimarySources(sources);
  const totalImpairedMiles = countyDetails.reduce(
    (total, county) => total + county.streamMiles.impaired,
    0
  );
  const totalActivePermits = countyDetails.reduce(
    (total, county) => total + county.permittingSummary.activePermits,
    0
  );
  const totalMonitoringStations = countyDetails.reduce(
    (total, county) => total + county.monitoringSummary.stations,
    0
  );
  const highestImpairmentCounties = [...countyDetails]
    .sort((a, b) => b.streamMiles.impaired - a.streamMiles.impaired)
    .slice(0, 5);

  return (
    <div className="shell space-y-6 py-6">
      <section className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="card bg-gradient-to-br from-white to-mist p-5 md:p-6">
          <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-normal">
            <span className="rounded-md bg-river px-3 py-2 text-white">Updated {latestRefresh}</span>
            <span className="rounded-md border border-ink/10 px-3 py-2 text-ink/65">
              {statewideCount} counties
            </span>
            <span className="rounded-md border border-ink/10 px-3 py-2 text-ink/65">
              {sources.length} source records
            </span>
          </div>
          <h1 className="mt-4 max-w-4xl text-3xl font-semibold tracking-normal text-ink sm:text-4xl">
            Tennessee river health and policy watch
          </h1>
          <div className="mt-5 flex flex-wrap gap-3 text-sm font-semibold">
            <Link
              href="#map"
              className="rounded-md bg-river px-4 py-3 text-white no-underline hover:bg-ink"
            >
              Open map
            </Link>
            <Link
              href="/counties"
              className="rounded-md border border-gold/35 bg-white/55 px-4 py-3 text-ink no-underline hover:border-gold hover:bg-gold/10"
            >
              Browse counties
            </Link>
            <Link
              href="/sources"
              className="rounded-md border border-gold/35 bg-white/55 px-4 py-3 text-ink no-underline hover:border-gold hover:bg-gold/10"
            >
              Verify sources
            </Link>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Coverage"
              value={formatNumber(statewideCount)}
              detail="county pages"
            />
            <MetricCard
              label="Impairment"
              value={formatNumber(totalImpairedMiles)}
              detail="county-summed stream miles"
            />
            <MetricCard
              label="Permits"
              value={formatNumber(totalActivePermits)}
              detail="active water features"
            />
            <MetricCard
              label="Monitoring"
              value={formatNumber(totalMonitoringStations)}
              detail="station records"
            />
          </div>
        </div>

        <aside className="card p-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-normal text-river">
                Source stack
              </p>
              <h2 className="mt-1 text-xl font-semibold">Primary feeds</h2>
            </div>
            <Link href="/sources" className="text-sm font-medium">
              Full registry
            </Link>
          </div>
          <div className="mt-3 max-h-[22rem] overflow-auto pr-1">
            {primarySources.map((source) => (
              <SourceTile key={source.dataset} source={source} />
            ))}
          </div>
        </aside>
      </section>

      <TennesseeMap counties={counties} countyDetails={countyDetails} />

      <section className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-3">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-normal text-river">
                Featured counties
              </p>
              <h2 className="mt-1 text-2xl font-semibold">Fast county reads</h2>
            </div>
            <Link href="/counties" className="text-sm font-medium">
              All counties
            </Link>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {featuredCountyDetails.map((county) => (
              <FeaturedCountyCard key={county.slug} county={county} />
            ))}
          </div>
        </div>

        <aside className="card p-4">
          <p className="text-xs font-semibold uppercase tracking-normal text-river">
            Highest impaired-mile snapshots
          </p>
          <ol className="mt-4 space-y-3 text-sm">
            {highestImpairmentCounties.map((county, index) => (
              <li key={county.slug} className="flex items-center justify-between gap-4">
                <Link href={`/counties/${county.slug}`} className="font-medium text-ink no-underline">
                  {index + 1}. {county.name}
                </Link>
                <span className="text-ink/65">{county.streamMiles.impaired.toFixed(1)} mi</span>
              </li>
            ))}
          </ol>
        </aside>
      </section>
    </div>
  );
}
