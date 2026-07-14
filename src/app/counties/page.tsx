import { CountyList } from "@/components/CountyList";
import { getCountyIndex } from "@/lib/data";

export default function CountiesPage() {
  const counties = getCountyIndex();
  const featured = counties.filter((county) => county.isFeatured);

  return (
    <div className="shell space-y-8 py-10">
      <section className="card p-7">
        <p className="text-xs uppercase tracking-normal text-river">County directory</p>
        <h1 className="mt-2 text-3xl font-semibold">All Tennessee counties</h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-ink/75">
          95 county pages with the same statewide map, water, policy, and source fields.
        </p>
      </section>

      <section className="space-y-5">
        <div>
          <p className="text-xs uppercase tracking-normal text-river">Featured cohort</p>
          <h2 className="mt-2 text-2xl font-semibold">Featured county reads</h2>
        </div>
        <CountyList counties={featured} />
      </section>

      <section className="space-y-5">
        <div>
          <p className="text-xs uppercase tracking-normal text-river">Statewide coverage</p>
          <h2 className="mt-2 text-2xl font-semibold">All 95 counties</h2>
        </div>
        <CountyList counties={counties} />
      </section>
    </div>
  );
}
