import Link from "next/link";
import type { Metadata } from "next";
import { rankingMetrics } from "@/lib/rankings";

export const metadata: Metadata = {
  title: "Statewide County Rankings | PolicyWatch",
  description: "Statewide ranking lists for PolicyWatch county-page attributes."
};

function groupedMetrics() {
  return Array.from(new Set(rankingMetrics.map((metric) => metric.group))).map((group) => ({
    group,
    metrics: rankingMetrics.filter((metric) => metric.group === group)
  }));
}

export default function RankingsPage() {
  const groups = groupedMetrics();

  return (
    <div className="shell space-y-8 py-10">
      <div className="flex flex-wrap items-center gap-2 text-sm text-ink/70">
        <Link href="/">Home</Link>
        <span>/</span>
        <span>Rankings</span>
      </div>

      <section className="card p-7">
        <p className="text-xs uppercase tracking-normal text-river">Statewide rankings</p>
        <h1 className="mt-2 text-3xl font-semibold">Compare all Tennessee counties</h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-ink/75">
          These lists use the same ranked attributes shown on individual county pages. Each list
          includes all 95 Tennessee counties and links back to the relevant county profile.
        </p>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        {groups.map((group) => (
          <article key={group.group} className="card p-6">
            <p className="text-xs uppercase tracking-normal text-river">{group.group}</p>
            <div className="mt-4 grid gap-3">
              {group.metrics.map((metric) => (
                <Link
                  key={metric.slug}
                  href={`/rankings/${metric.slug}`}
                  className="rounded-md border border-ink/10 bg-sand px-4 py-3 text-sm font-semibold text-ink no-underline transition hover:border-gold/45 hover:bg-white hover:text-river"
                >
                  {metric.label}
                </Link>
              ))}
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
