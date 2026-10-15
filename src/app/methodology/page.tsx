import Link from "next/link";

export default function MethodologyPage() {
  return (
    <div className="shell py-10">
      <article className="card max-w-4xl p-8">
        <p className="text-xs uppercase tracking-normal text-river">Methodology</p>
        <h1 className="mt-2 text-3xl font-semibold">Static data method</h1>
        <div className="mt-6 space-y-5 text-sm leading-7 text-ink/75">
          <p>
            Public pages render from locally saved data files and simplified map shapes so the
            site can run without a live backend.
          </p>
          <p>
            Data refreshes download online agency records and rebuild county summaries and map layers.
            The Sources page records successful refresh dates, failed checks, and local snapshots that
            require manual replacement.
          </p>
          <p><Link href="/glossary">Acronyms and map terms explained</Link></p>
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
