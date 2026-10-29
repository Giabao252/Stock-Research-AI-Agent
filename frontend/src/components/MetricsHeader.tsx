import type { DisplayMetrics } from '../lib/metrics'
import { formatCompactUsd, formatPrice, formatRatio, formatSignedPercent } from '../lib/format'
import { Skeleton } from './states'

interface Props {
  ticker: string
  company: string
  metrics: DisplayMetrics | null
  /** metrics arrive with the finished report, so show placeholders until then */
  loading: boolean
}

function Cell({ label, value, loading, tone }: { label: string; value: string | null; loading: boolean; tone?: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs uppercase tracking-wide text-gray-500">{label}</dt>
      <dd className={`mt-1 truncate text-lg font-semibold tabular-nums ${tone ?? 'text-gray-100'}`}>
        {loading ? <Skeleton className="h-6 w-20" /> : (value ?? '—')}
      </dd>
    </div>
  )
}

export function MetricsHeader({ ticker, company, metrics, loading }: Props) {
  const change = metrics?.changePercent ?? null
  const changeTone = change === null ? undefined : change >= 0 ? 'text-emerald-300' : 'text-rose-300'

  return (
    <header className="rounded-2xl border border-gray-800 bg-gray-900/50 p-5">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h1 className="text-2xl font-bold tracking-tight text-gray-100">{ticker}</h1>
        <p className="text-gray-400">{company}</p>
      </div>
      <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-4">
        <div className="min-w-0">
          <dt className="text-xs uppercase tracking-wide text-gray-500">Price</dt>
          <dd className="mt-1 flex items-baseline gap-2 truncate text-lg font-semibold tabular-nums text-gray-100">
            {loading ? (
              <Skeleton className="h-6 w-20" />
            ) : (
              <>
                {metrics?.price != null ? formatPrice(metrics.price) : '—'}
                {change !== null && <span className={`text-xs font-medium ${changeTone}`}>{formatSignedPercent(change)}</span>}
              </>
            )}
          </dd>
        </div>
        <Cell label="P/E" loading={loading} value={metrics?.peRatio != null ? formatRatio(metrics.peRatio) : null} />
        <Cell label="Market cap" loading={loading} value={metrics?.marketCap != null ? formatCompactUsd(metrics.marketCap) : null} />
        <Cell label="Revenue (TTM)" loading={loading} value={metrics?.revenueTtm != null ? formatCompactUsd(metrics.revenueTtm) : null} />
      </dl>
      {loading && <p className="mt-4 text-xs text-gray-500">Live market data is attached when the report finishes.</p>}
    </header>
  )
}
