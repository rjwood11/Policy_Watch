import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getCounty, getCountyIndex } from "@/lib/data";
import { getCountyRankingRows, getRankingMetric, rankingMetrics } from "@/lib/rankings";

export const dynamicParams = false;

export function generateStaticParams() {
  return rankingMetrics.map((metric) => ({ metric: metric.slug }));
}

export async function generateMetadata({
  params
}: {
  params: Promise<{ metric: string }>;
}): Promise<Metadata> {
  const { metric: metricSlug } = await params;
  const metric = getRankingMetric(metricSlug);

  if (!metric) {
    return {
      title: "Ranking Not Found"
    };
  }

  return {
    title: `${metric.label} Rankings | PolicyWatch`,
    description: `Statewide Tennessee county rankings for ${metric.label.toLowerCase()}.`
  };
}

function rankLabel(rank: number | undefined) {
  return rank ? `#${rank.toLocaleString()}` : "n/a";
}

export default async function RankingDetailPage({
  params
}: {
  params: Promise<{ metric: string }>;
}) {
  const { metric: metricSlug } = await params;
  const metric = getRankingMetric(metricSlug);

  if (!metric) {
    notFound();
  }

  const counties = getCountyIndex().map((county) => getCounty(county.slug));
  const rows = getCountyRankingRows(counties, metric);
  const rankedRows = rows.filter((row) => row.rank).length;
  const basis = rows.find((row) => row.rank)?.rank?.basis ?? "Ranked high to low.";

  return (
    <div className="shell space-y-8 py-10">
      <div className="flex flex-wrap items-center gap-2 text-sm text-ink/70">
        <Link href="/">Home</Link>
        <span>/</span>
        <Link href="/rankings">Rankings</Link>
        <span>/</span>
        <span>{metric.label}</span>
      </div>

      <section className="card p-7">
        <p className="text-xs uppercase tracking-normal text-river">{metric.group}</p>
        <h1 className="mt-2 text-3xl font-semibold">{metric.label} rankings</h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-ink/75">
          {basis} This table includes {rankedRows.toLocaleString()} ranked Tennessee counties
          from the same county-page data snapshot.
        </p>
        <Link href="/rankings" className="mt-5 inline-block text-sm font-medium">
          View all ranking categories
        </Link>
      </section>

      <section className="card overflow-hidden">
        <div className="border-b border-ink/10 px-5 py-4">
          <p className="text-xs uppercase tracking-normal text-river">All Tennessee counties</p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse text-left text-sm">
            <thead className="bg-sand text-xs uppercase tracking-normal text-ink/60">
              <tr>
                <th scope="col" className="px-4 py-3 font-semibold">
                  Rank
                </th>
                <th scope="col" className="px-4 py-3 font-semibold">
                  County
                </th>
                <th scope="col" className="px-4 py-3 font-semibold">
                  Region
                </th>
                <th scope="col" className="px-4 py-3 text-right font-semibold">
                  {metric.valueLabel}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink/10">
              {rows.map((row) => (
                <tr key={row.county.slug} id={row.county.slug} className="rank-row scroll-mt-24">
                  <td className="whitespace-nowrap px-4 py-3 align-top font-semibold text-ink">
                    {rankLabel(row.rank?.rank)}
                    {row.rank && row.rank.tieCount > 1 ? (
                      <span className="mt-1 block text-xs font-normal text-ink/55">
                        tie of {row.rank.tieCount}
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 align-top">
                    <Link
                      href={`/counties/${row.county.slug}`}
                      className="font-semibold text-ink no-underline hover:text-river hover:underline"
                    >
                      {row.county.name} County
                    </Link>
                  </td>
                  <td className="px-4 py-3 align-top text-ink/65">{row.county.region}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right align-top font-medium text-ink">
                    {row.value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
