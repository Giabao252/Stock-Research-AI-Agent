import type { ComparisonColumn } from '../hooks/useMultiCompare'
import { isActive } from '../hooks/runStore'
import { formatCompactUsd, formatPrice, formatRatio } from '../lib/format'
import { extractMetrics, type DisplayMetrics } from '../lib/metrics'
import { Skeleton } from './states'
import { VerdictBadge } from './VerdictBadge'

const ROWS: Array<{ label: string; format: (m: DisplayMetrics) => string | null }> = [
  { label: 'Price', format: (m) => (m.price === null ? null : formatPrice(m.price)) },
  { label: 'P/E', format: (m) => (m.peRatio === null ? null : formatRatio(m.peRatio)) },
  { label: 'Market cap', format: (m) => (m.marketCap === null ? null : formatCompactUsd(m.marketCap)) },
  { label: 'Revenue (TTM)', format: (m) => (m.revenueTtm === null ? null : formatCompactUsd(m.revenueTtm)) },
]

/** Verdict + key figures at a glance; each column fills in as soon as its own run finishes. */
export function ComparisonMetrics({ columns }: { columns: readonly ComparisonColumn[] }) {
  const cell = (column: ComparisonColumn, render: () => string | null) => {
    if (column.run && isActive(column.run)) return <Skeleton className="h-5 w-16" />
    return render() ?? '—'
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-gray-800 bg-gray-900/40">
      <table className="w-full min-w-[28rem] text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-left text-xs uppercase tracking-wide text-gray-500">
            <th scope="col" className="px-4 py-3 font-medium">&nbsp;</th>
            {columns.map((c) => (
              <th key={c.ticker} scope="col" className="px-4 py-3 font-semibold text-gray-200">
                {c.ticker}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-gray-800">
            <th scope="row" className="px-4 py-3 text-left font-normal text-gray-400">Verdict</th>
            {columns.map((c) => (
              <td key={c.ticker} className="px-4 py-3">
                {c.run && isActive(c.run) ? (
                  <Skeleton className="h-6 w-20" />
                ) : c.report ? (
                  <VerdictBadge verdict={c.report.verdict} confidence={c.report.confidence} />
                ) : (
                  '—'
                )}
              </td>
            ))}
          </tr>
          {ROWS.map((row) => (
            <tr key={row.label} className="border-b border-gray-800 last:border-0">
              <th scope="row" className="px-4 py-3 text-left font-normal text-gray-400">{row.label}</th>
              {columns.map((c) => (
                <td key={c.ticker} className="px-4 py-3 tabular-nums text-gray-200">
                  {cell(c, () => (c.report ? row.format(extractMetrics(c.report.metrics)) : null))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
