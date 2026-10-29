import { useParams } from 'react-router-dom'
import type { ResearchReport } from '../api/schemas'
import { Button, ButtonLink } from '../components/Button'
import { ClaimDiff } from '../components/ClaimDiff'
import { ArrowRightIcon, RefreshIcon } from '../components/icons'
import { Banner, ErrorPanel, Skeleton } from '../components/states'
import { VerdictBadge } from '../components/VerdictBadge'
import { useReportCompare } from '../hooks/useReportCompare'
import { companyName } from '../lib/companies'
import { formatDateTime } from '../lib/dates'
import { formatCompactUsd, formatConfidence, formatPrice, formatRatio } from '../lib/format'
import { extractMetrics } from '../lib/metrics'
import { VERDICT_STYLES } from '../lib/verdict'

const SIGNIFICANT_CONFIDENCE_DELTA = 0.1

function MetricRow({ label, older, newer }: { label: string; older: string | null; newer: string | null }) {
  return (
    <tr className="border-t border-gray-800">
      <th scope="row" className="py-2 pr-4 text-left text-sm font-normal text-gray-400">
        {label}
      </th>
      <td className="py-2 pr-4 text-sm tabular-nums text-gray-200">{older ?? '—'}</td>
      <td className="py-2 text-sm tabular-nums text-gray-200">{newer ?? '—'}</td>
    </tr>
  )
}

function MetricsTable({ older, newer }: { older: ResearchReport; newer: ResearchReport }) {
  const a = extractMetrics(older.metrics)
  const b = extractMetrics(newer.metrics)
  const money = (v: number | null) => (v === null ? null : formatCompactUsd(v))
  return (
    <section aria-labelledby="metrics-heading" className="rounded-2xl border border-gray-800 bg-gray-900/40 p-5">
      <h2 id="metrics-heading" className="text-sm font-semibold uppercase tracking-wide text-gray-400">
        Key metrics
      </h2>
      <table className="mt-3 w-full">
        <thead>
          <tr className="text-left text-xs text-gray-500">
            <th scope="col" className="pb-2 font-normal">&nbsp;</th>
            <th scope="col" className="pb-2 font-normal">Older report</th>
            <th scope="col" className="pb-2 font-normal">Newer report</th>
          </tr>
        </thead>
        <tbody>
          <MetricRow label="Price" older={a.price === null ? null : formatPrice(a.price)} newer={b.price === null ? null : formatPrice(b.price)} />
          <MetricRow label="P/E" older={a.peRatio === null ? null : formatRatio(a.peRatio)} newer={b.peRatio === null ? null : formatRatio(b.peRatio)} />
          <MetricRow label="Market cap" older={money(a.marketCap)} newer={money(b.marketCap)} />
          <MetricRow label="Revenue (TTM)" older={money(a.revenueTtm)} newer={money(b.revenueTtm)} />
        </tbody>
      </table>
      <p className="mt-3 text-xs text-gray-500">Figures are the values recorded with each report.</p>
    </section>
  )
}

export default function ReportCompare() {
  const { id1 = '', id2 = '' } = useParams()
  const { status, error, comparison, reload } = useReportCompare(id1, id2)

  if (status === 'error') {
    return (
      <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
        <ErrorPanel
          title="Couldn’t load these reports"
          message={error ?? 'Something went wrong.'}
          action={
            <>
              <Button variant="primary" onClick={reload}>
                <RefreshIcon /> Try again
              </Button>
              <ButtonLink to="/history">Back to history</ButtonLink>
            </>
          }
        />
      </main>
    )
  }

  if (!comparison) {
    return (
      <main className="mx-auto flex w-full max-w-5xl flex-col gap-4 px-4 py-8 sm:px-6" role="status" aria-label="Loading comparison">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </main>
    )
  }

  const { older, newer } = comparison
  const ticker = older.ticker
  const delta = comparison.confidenceDelta
  const bigShift = Math.abs(delta) >= SIGNIFICANT_CONFIDENCE_DELTA

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8 sm:px-6">
      <header>
        <ButtonLink variant="ghost" size="sm" to="/history" className="-ml-3">
          ← History
        </ButtonLink>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-gray-100">
          {companyName(ticker)} <span className="text-gray-400">({ticker})</span> — report comparison
        </h1>
      </header>

      {!comparison.sameTicker && (
        <Banner tone="warning" title="These reports are for different tickers">
          {older.ticker} and {newer.ticker} aren’t directly comparable over time.
        </Banner>
      )}

      {comparison.verdictChanged ? (
        <div
          role="status"
          className="flex flex-wrap items-center gap-3 rounded-2xl border border-indigo-400/40 bg-indigo-500/10 px-5 py-4 text-lg font-semibold text-gray-100"
        >
          Verdict changed:
          <span className={VERDICT_STYLES[older.verdict].text}>{VERDICT_STYLES[older.verdict].label}</span>
          <ArrowRightIcon className="h-5 w-5 text-gray-400" />
          <span className={VERDICT_STYLES[newer.verdict].text}>{VERDICT_STYLES[newer.verdict].label}</span>
        </div>
      ) : (
        <p className="text-sm text-gray-400">
          Verdict unchanged: <span className={VERDICT_STYLES[newer.verdict].text}>{VERDICT_STYLES[newer.verdict].label}</span>
        </p>
      )}

      <section className="grid gap-4 sm:grid-cols-2" aria-label="Verdict and confidence">
        {[
          { label: 'Older', report: older },
          { label: 'Newer', report: newer },
        ].map(({ label, report }) => (
          <div key={label} className="rounded-2xl border border-gray-800 bg-gray-900/50 p-5">
            <p className="text-xs uppercase tracking-wide text-gray-500">{label} · {formatDateTime(report.generated_at)}</p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <VerdictBadge verdict={report.verdict} size="lg" />
              <span className="text-sm tabular-nums text-gray-300">{formatConfidence(report.confidence)} confidence</span>
            </div>
          </div>
        ))}
      </section>

      <p
        className={`text-sm ${bigShift ? 'font-semibold text-amber-300' : 'text-gray-400'}`}
        role={bigShift ? 'status' : undefined}
      >
        Confidence {formatConfidence(older.confidence)} → {formatConfidence(newer.confidence)}{' '}
        ({delta >= 0 ? '+' : ''}
        {Math.round(delta * 100)} pts){bigShift && ' — a significant shift'}
      </p>

      <MetricsTable older={older} newer={newer} />

      {[
        { title: 'Bull case', diff: comparison.bull, tone: 'text-emerald-300' },
        { title: 'Bear case', diff: comparison.bear, tone: 'text-rose-300' },
      ].map(({ title, diff, tone }) => (
        <section key={title} aria-label={title}>
          <h2 className={`mb-3 text-lg font-semibold ${tone}`}>{title}</h2>
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <h3 className="mb-2 text-xs uppercase tracking-wide text-gray-500">Older · {formatDateTime(older.generated_at)}</h3>
              <ClaimDiff entries={diff.older} />
            </div>
            <div>
              <h3 className="mb-2 text-xs uppercase tracking-wide text-gray-500">Newer · {formatDateTime(newer.generated_at)}</h3>
              <ClaimDiff entries={diff.newer} />
            </div>
          </div>
        </section>
      ))}
    </main>
  )
}
