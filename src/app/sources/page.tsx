import { DataSourceTable } from "@/components/DataSourceTable";
import { getDataSources, getLastUpdated } from "@/lib/data";

export default function SourcesPage() {
  const sources = getDataSources();
  const lastUpdated = getLastUpdated();

  return (
    <div className="shell space-y-6 py-10">
      <div>
        <p className="text-xs uppercase tracking-normal text-river">Sources</p>
        <h1 className="mt-2 text-3xl font-semibold">Data source registry</h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-ink/75">
          Refresh dates and source links for the county, watershed, water-quality, permitting,
          screening, and district datasets.
        </p>
      </div>
      <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        {Object.entries(lastUpdated).map(([key, value]) => (
          <article key={key} className="card p-4">
            <p className="text-xs uppercase tracking-normal text-river">{key.replaceAll("-", " ")}</p>
            <p className="mt-2 text-sm font-medium text-ink">{value}</p>
          </article>
        ))}
      </section>
      <DataSourceTable sources={sources} />
    </div>
  );
}
