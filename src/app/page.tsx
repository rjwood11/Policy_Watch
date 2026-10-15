import Link from "next/link";
import type { Metadata } from "next";
import { TennesseeMap } from "@/components/TennesseeMap";
import type { CountyRecord } from "@/lib/data";
import { getCounty, getCountyIndex, getLastUpdated } from "@/lib/data";

export const metadata: Metadata = {
  title: "Harpeth Conservancy's Water Policy Watch",
  description:
    "County-level Tennessee water quality, permitting, monitoring, and policy context from Harpeth Conservancy."
};

function getLatestRefresh(lastUpdated: Record<string, string>) {
  const dates = Object.values(lastUpdated).sort();
  return dates[dates.length - 1] ?? "n/a";
}

function CompactFeaturedCountyCard({ county }: { county: CountyRecord }) {
  return (
    <Link
      href={`/counties/${county.slug}`}
      className="block rounded-md border border-ink/10 bg-sand/75 px-3 py-2 no-underline transition hover:border-gold/45 hover:bg-white"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-ink">{county.name} County</p>
          <p className="mt-0.5 text-xs text-ink/60">{county.region}</p>
        </div>
        <span className="shrink-0 text-xs font-semibold text-river">
          {county.streamMiles.impaired.toFixed(1)} mi
        </span>
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-2 text-xs text-ink/65">
        <div className="flex items-center justify-between gap-2">
          <dt className="text-ink/60">Impaired</dt>
          <dd className="font-semibold text-ink">{county.streamMiles.impaired.toFixed(1)} mi</dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="text-ink/60">Permits</dt>
          <dd className="font-semibold text-ink">
            {county.permittingSummary.activePermits.toLocaleString()}
          </dd>
        </div>
      </dl>
    </Link>
  );
}

export default function HomePage() {
  const counties = getCountyIndex();
  const countyDetails = counties.map((county) => getCounty(county.slug));
  const lastUpdated = getLastUpdated();
  const latestRefresh = getLatestRefresh(lastUpdated);
  const featuredCountyDetails = countyDetails.filter((county) => county.isFeatured);
  const highestImpairmentCounties = [...countyDetails]
    .sort((a, b) => b.streamMiles.impaired - a.streamMiles.impaired)
    .slice(0, 5);

  return (
    <div className="shell space-y-6 py-6">
      <section className="card border-river/30 bg-white p-7 md:p-9">
        <h1 className="max-w-none whitespace-nowrap text-xs font-bold leading-tight tracking-normal text-black min-[380px]:text-sm sm:text-2xl md:text-3xl lg:text-4xl">
          Harpeth Conservancy&apos;s Water Policy Watch
        </h1>
        <p className="mt-2 text-xs text-ink/60">
          Updated on <time dateTime={latestRefresh}>{latestRefresh}</time>
        </p>
      </section>

      <section>
        <TennesseeMap counties={counties} countyDetails={countyDetails} />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="card p-4">
          <p className="text-xs font-semibold uppercase tracking-normal text-river">Snapshot</p>
          <h2 className="mt-1 text-lg font-semibold">Highest impaired-mile counties</h2>
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
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-normal text-river">
                Featured counties
              </p>
              <h2 className="mt-1 text-lg font-semibold">Fast county reads</h2>
            </div>
            <Link href="/counties" className="text-sm font-medium">
              All counties
            </Link>
          </div>
          <div className="mt-3 grid gap-2 md:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            {featuredCountyDetails.map((county) => (
              <CompactFeaturedCountyCard key={county.slug} county={county} />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
