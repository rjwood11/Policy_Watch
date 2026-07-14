export default function MethodologyPage() {
  return (
    <div className="shell py-10">
      <article className="card max-w-4xl p-8">
        <p className="text-xs uppercase tracking-normal text-river">Methodology</p>
        <h1 className="mt-2 text-3xl font-semibold">Static data method</h1>
        <div className="mt-6 space-y-5 text-sm leading-7 text-ink/75">
          <p>
            Public pages render from local exported JSON and simplified geospatial assets so the
            site can run without a live backend.
          </p>
          <p>
            County summary JSON, layer metadata, search indexes, and source metadata can later be
            regenerated from PostGIS and scheduled ETL jobs without changing the route structure.
          </p>
          <p>
            Screening indicators should be presented as context, not as absolute truth.
            Every public-facing metric should eventually include a plain-language
            definition, source note, update timestamp, and caveat.
          </p>
        </div>
      </article>
    </div>
  );
}
