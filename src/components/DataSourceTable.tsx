import type { DataSourceRecord } from "@/lib/data";

export function DataSourceTable({ sources }: { sources: DataSourceRecord[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-river text-white">
            <tr>
              <th className="px-4 py-3 font-medium">Dataset</th>
              <th className="px-4 py-3 font-medium">Purpose</th>
              <th className="px-4 py-3 font-medium">Source</th>
              <th className="px-4 py-3 font-medium">Refresh</th>
              <th className="px-4 py-3 font-medium">Last updated</th>
              <th className="px-4 py-3 font-medium">Notes</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.dataset} className="border-t border-ink/10 align-top">
                <td className="min-w-52 px-4 py-4 font-medium">
                  <div>{source.dataset}</div>
                </td>
                <td className="min-w-64 px-4 py-4 leading-6 text-ink/75">{source.purpose}</td>
                <td className="min-w-60 px-4 py-4 leading-6">
                  {source.sourceUrl.startsWith("http") ? (
                    <a href={source.sourceUrl} target="_blank" rel="noreferrer">
                      {source.sourceName}
                    </a>
                  ) : (
                    <span>{source.sourceName}</span>
                  )}
                </td>
                <td className="min-w-40 px-4 py-4 text-ink/75">{source.refreshFrequency}</td>
                <td className="min-w-36 px-4 py-4 text-ink/75">{source.lastUpdated}</td>
                <td className="min-w-80 px-4 py-4 leading-6 text-ink/75">{source.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
