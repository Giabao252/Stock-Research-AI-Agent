import { Link } from 'react-router-dom'
import { Button, ButtonLink } from '../components/Button'
import { RefreshIcon, TrashIcon } from '../components/icons'
import { EmptyState, ErrorPanel, Skeleton } from '../components/states'
import { VerdictBadge } from '../components/VerdictBadge'
import { useHistory, type HistoryRow } from '../hooks/useHistory'
import { useStartRun } from '../hooks/useStartRun'
import { companyName } from '../lib/companies'
import { formatDateTime } from '../lib/dates'

function SkeletonRows() {
  return (
    <ul className="flex flex-col gap-3" role="status" aria-label="Loading reports">
      {Array.from({ length: 4 }, (_, i) => (
        <li key={i} className="flex items-center gap-4 rounded-xl border border-gray-800 bg-gray-900/40 p-4">
          <Skeleton className="h-5 w-5" />
          <div className="flex-1">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="mt-2 h-3 w-28" />
          </div>
          <Skeleton className="h-6 w-24" />
        </li>
      ))}
    </ul>
  )
}

interface RowProps {
  row: HistoryRow
  selected: boolean
  onToggle: () => void
  onDelete: () => void
  onRerun: () => void
}

function ReportRow({ row, selected, onToggle, onDelete, onRerun }: RowProps) {
  const { report, reportId, ticker } = row
  return (
    <li
      className={`flex flex-wrap items-center gap-x-4 gap-y-3 rounded-xl border p-4 transition-colors motion-reduce:transition-none ${
        selected ? 'border-indigo-400/60 bg-indigo-500/5' : 'border-gray-800 bg-gray-900/40'
      }`}
    >
      <input
        type="checkbox"
        checked={selected}
        onChange={onToggle}
        aria-label={`Select ${ticker} report from ${formatDateTime(report.generated_at)} to compare`}
        className="h-4 w-4 shrink-0 accent-indigo-500"
      />
      <div className="min-w-0 flex-1">
        <Link
          to={`/report/${ticker}?id=${reportId}`}
          className="font-semibold text-gray-100 hover:underline focus-visible:outline-2 focus-visible:outline-indigo-400"
        >
          {companyName(ticker)} <span className="text-gray-400">({ticker})</span>
        </Link>
        <p className="mt-0.5 text-xs text-gray-500">{formatDateTime(report.generated_at)}</p>
      </div>
      <VerdictBadge verdict={report.verdict} confidence={report.confidence} />
      <div className="flex gap-2">
        <Button size="sm" onClick={onRerun}>
          <RefreshIcon /> Re-run
        </Button>
        <Button size="sm" variant="ghost" onClick={onDelete} aria-label={`Delete ${ticker} report`}>
          <TrashIcon />
        </Button>
      </div>
    </li>
  )
}

export default function History() {
  const history = useHistory()
  const startRun = useStartRun()

  const [first, second] = history.compareIds

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-100">Report history</h1>
          <p className="mt-1 text-sm text-gray-400">Select two reports for the same ticker to see how the analysis changed.</p>
        </div>
        {history.canCompare ? (
          <ButtonLink variant="primary" to={`/history/compare/${first}/${second}`}>
            Compare selected
          </ButtonLink>
        ) : (
          <Button variant="primary" disabled>
            Compare selected
          </Button>
        )}
      </header>

      {history.compareHint && (
        <p role="status" className="text-sm text-amber-300">
          {history.compareHint}
        </p>
      )}

      {history.isLoading && <SkeletonRows />}

      {history.error && (
        <ErrorPanel
          title="Couldn’t load your reports"
          message={history.error}
          action={
            <Button variant="primary" onClick={history.retry}>
              <RefreshIcon /> Try again
            </Button>
          }
        />
      )}

      {!history.isLoading && !history.error && history.rows.length === 0 && (
        <EmptyState
          title="No reports yet"
          action={<ButtonLink variant="primary" to="/">Research a stock</ButtonLink>}
        >
          Reports you generate show up here so you can revisit, re-run and compare them.
        </EmptyState>
      )}

      {history.failedCount > 0 && (
        <p role="status" className="text-sm text-amber-300">
          {history.failedCount} report{history.failedCount === 1 ? '' : 's'} couldn’t be loaded right now.
          <button type="button" onClick={history.retry} className="ml-2 underline hover:text-amber-200">
            Retry
          </button>
        </p>
      )}

      {history.rows.length > 0 && (
        <ul className="flex flex-col gap-3">
          {history.rows.map((row) => (
            <ReportRow
              key={row.reportId}
              row={row}
              selected={history.selected.includes(row.reportId)}
              onToggle={() => history.toggleSelected(row.reportId)}
              onDelete={() => history.requestDelete(row.reportId)}
              onRerun={() => startRun(row.ticker)}
            />
          ))}
        </ul>
      )}
    </main>
  )
}
