import type { CountyRecord } from "@/lib/data";

export function IndicatorCard({
  indicator
}: {
  indicator: CountyRecord["indicators"][number];
}) {
  return (
    <article className="card p-5">
      <p className="text-xs uppercase tracking-normal text-river">{indicator.key}</p>
      <h3 className="mt-2 text-lg font-semibold">{indicator.label}</h3>
      <p className="mt-3 text-3xl font-semibold">{indicator.value}</p>
      {indicator.stateRank ? (
        <div className="mt-3 border-t border-ink/10 pt-3">
          <p className="text-xs font-semibold uppercase tracking-normal text-river">
            State rank {indicator.stateRank.display}
          </p>
          <p className="mt-1 text-xs leading-5 text-ink/60">{indicator.stateRank.basis}</p>
        </div>
      ) : null}
      <p className="mt-3 text-sm leading-6 text-ink/75">{indicator.definition}</p>
      <p className="mt-4 text-xs uppercase tracking-normal text-river">
        {indicator.sourceDataset} - updated {indicator.updatedAt}
      </p>
      <p className="mt-4 text-xs leading-5 text-ink/60">Caveat: {indicator.caveat}</p>
    </article>
  );
}
