import type { DataSourceRecord } from "@/lib/data";

export function DataSourceTable({ sources }: { sources: DataSourceRecord[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-[920px] table-fixed text-left text-[0.8125rem]">
          <colgroup>
            <col className="w-[14rem]" />
            <col className="w-[17rem]" />
            <col className="w-[15rem]" />
            <col className="w-[9rem]" />
            <col className="w-[8rem]" />
            <col />
          </colgroup>
          <thead className="bg-river text-white">
            <tr>
              <th className="px-3 py-3 font-medium">Dataset</th>
              <th className="px-3 py-3 font-medium">Purpose</th>
              <th className="px-3 py-3 font-medium">Source</th>
              <th className="px-3 py-3 font-medium">Refresh</th>
              <th className="px-3 py-3 font-medium">Updated</th>
              <th className="px-3 py-3 font-medium">Notes</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.dataset} className="border-t border-ink/10 align-top">
                <td className="px-3 py-3 font-medium">
                  <div>{source.dataset}</div>
                </td>
                <td className="px-3 py-3 leading-5 text-ink/75">{source.purpose}</td>
                <td className="px-3 py-3 leading-5">
                  {source.sourceUrl.startsWith("http") ? (
                    <a href={source.sourceUrl} target="_blank" rel="noreferrer">
                      {source.sourceName}
                    </a>
                  ) : (
                    <span>{source.sourceName}</span>
                  )}
                </td>
                <td className="px-3 py-3 text-ink/75">{source.refreshFrequency}</td>
                <td className="px-3 py-3 text-ink/75">{source.lastUpdated}</td>
                <td className="px-3 py-3 leading-5 text-ink/75">{source.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
