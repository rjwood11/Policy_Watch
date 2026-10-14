export type LayerKey = "watershed" | "utilities" | "protected" | "landfills" | "superfund" | "landuse" | "districts" | "impaired" | "permits" | "echo";

export type LegendGroup = {
  key: LayerKey;
  label: string;
  entries: Array<{
    label: string;
    color: string;
    borderColor?: string;
    symbol: "line" | "dashed" | "area" | "point";
    count?: number;
  }>;
  status?: string;
  note?: string;
};

export function CountyMapLegend({ groups }: { groups: LegendGroup[] }) {
  return (
    <section aria-labelledby="county-map-legend-title" className="rounded-lg bg-ink p-5 text-white">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id="county-map-legend-title" className="text-xs uppercase tracking-normal text-white/70">Legend</h3>
        <span className="rounded-full bg-white/10 px-2 py-1 text-xs text-white/80" role="status">
          {groups.length} {groups.length === 1 ? "layer" : "layers"} selected
        </span>
      </div>
      {groups.length === 0 ? (
        <p className="mt-4 text-sm leading-6 text-white/75">Select a layer above to see its map symbols.</p>
      ) : (
        <div className="mt-4 divide-y divide-white/15">
          {groups.map((group) => (
            <div key={group.key} className="py-4 first:pt-0 last:pb-0">
              <h4 className="text-sm font-semibold text-white">{group.label}</h4>
              {group.status ? <p className="mt-2 text-xs leading-5 text-white/70" role="status">{group.status}</p> : null}
              {group.entries.length > 0 ? (
                <ul className="mt-3 space-y-3 text-sm">
                  {group.entries.map((entry) => (
                    <li key={entry.label} className="flex items-start justify-between gap-3">
                      <span className="flex items-center gap-3">
                        <span className="flex h-5 w-7 shrink-0 items-center justify-center" aria-hidden="true">
                          {entry.symbol === "line" || entry.symbol === "dashed" ? (
                            <span className="w-7 border-t-[3px]" style={{ borderColor: entry.color, borderStyle: entry.symbol === "dashed" ? "dashed" : "solid" }} />
                          ) : (
                            <span
                              className={entry.symbol === "point" ? "h-3 w-3 rounded-full border-2 border-white" : "h-4 w-4 rounded-sm border"}
                              style={{ backgroundColor: entry.color, borderColor: entry.symbol === "point" ? "white" : entry.borderColor || entry.color }}
                            />
                          )}
                        </span>
                        <span>{entry.label}</span>
                      </span>
                      {entry.count !== undefined && !group.status ? (
                        <span className="shrink-0 tabular-nums text-white/75" aria-label={`${entry.count.toLocaleString()} loaded records`}>
                          {entry.count.toLocaleString()}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : null}
              {group.note ? <p className="mt-3 text-xs leading-5 text-white/70">{group.note}</p> : null}
            </div>
          ))}
        </div>
      )}
      {groups.some((group) => !group.status && group.entries.some((entry) => entry.count !== undefined)) ? (
        <p className="mt-4 border-t border-white/15 pt-3 text-xs leading-5 text-white/60">Counts reflect loaded records, not the current zoom.</p>
      ) : null}
    </section>
  );
}
