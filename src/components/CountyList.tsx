import Link from "next/link";
import type { CountyIndexRecord } from "@/lib/data";

export function CountyList({ counties }: { counties: CountyIndexRecord[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {counties.map((county) => (
        <Link
          key={county.slug}
          href={`/counties/${county.slug}`}
          className="card p-5 no-underline"
        >
          <p className="text-xs uppercase tracking-normal text-river">{county.region}</p>
          <p className="mt-3 inline-flex rounded-full bg-gold/15 px-3 py-1 text-[11px] font-medium uppercase tracking-normal text-ink">
            {county.isFeatured ? "Featured page" : county.hasPage ? "County page live" : "Map only"}
          </p>
          <h3 className="mt-2 text-xl font-semibold text-ink">{county.name}</h3>
          <p className="mt-3 text-sm leading-6 text-ink/75">{county.summary}</p>
        </Link>
      ))}
    </div>
  );
}
