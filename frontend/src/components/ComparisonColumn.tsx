import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Claim, ResearchReport } from '../api/schemas'
import type { ComparisonColumn as Column } from '../hooks/useMultiCompare'
import { isActive } from '../hooks/runStore'
import { useReportCitations } from '../hooks/useCitations'
import { summarizeToolCall } from '../lib/toolSummary'
import { CitationMarker } from './CitationMarker'
import { ChevronIcon, SpinnerIcon } from './icons'
import { ErrorPanel } from './states'
import { VerdictBadge } from './VerdictBadge'

const TOP_CLAIMS = 3

function ExpandableClaim({ claim, number, onOpenCitation }: { claim: Claim; number: number; onOpenCitation: (c: Claim, n: number) => void }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <li className="rounded-lg border border-gray-800 bg-gray-900/40 text-sm">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="flex w-full items-start gap-2 rounded-lg px-3 py-2 text-left text-gray-200 hover:bg-gray-800/40 focus-visible:outline-2 focus-visible:outline-indigo-400"
      >
        <span className={`min-w-0 flex-1 leading-relaxed ${expanded ? '' : 'line-clamp-3'}`}>{claim.text}</span>
        <ChevronIcon className={`mt-1 h-3.5 w-3.5 shrink-0 text-gray-500 transition-transform motion-reduce:transition-none ${expanded ? 'rotate-180' : ''}`} />
      </button>
      {expanded && (
        <p className="flex items-center gap-1 border-t border-gray-800 px-3 py-2 text-xs text-gray-400">
          <CitationMarker number={number} onClick={() => onOpenCitation(claim, number)} />
          <span className="min-w-0 break-words">{claim.doc_name}</span>
        </p>
      )}
    </li>
  )
}

function Results({ report, onOpenCitation }: { report: ResearchReport; onOpenCitation: (c: Claim, n: number) => void }) {
  const citations = useReportCitations(report)
  const sections = [
    { title: 'Bull case', claims: report.bull_case, tone: 'text-emerald-300' },
    { title: 'Bear case', claims: report.bear_case, tone: 'text-rose-300' },
  ]
  return (
    <div className="flex flex-col gap-5">
      {report.partial && <p className="text-xs text-amber-300">Partial report{report.partial_reason ? ` — ${report.partial_reason}` : ''}</p>}
      {sections.map(({ title, claims, tone }) => (
        <section key={title}>
          <h4 className={`mb-2 text-sm font-semibold ${tone}`}>{title}</h4>
          <ul className="flex flex-col gap-2">
            {claims.slice(0, TOP_CLAIMS).map((claim, i) => (
              <ExpandableClaim key={i} claim={claim} number={citations.numberFor(claim)} onOpenCitation={onOpenCitation} />
            ))}
          </ul>
          {claims.length > TOP_CLAIMS && <p className="mt-2 text-xs text-gray-500">+{claims.length - TOP_CLAIMS} more in the full report</p>}
        </section>
      ))}
    </div>
  )
}

interface Props {
  column: Column
  onOpenCitation: (claim: Claim, number: number) => void
}

/** One ticker's independent lane: its own progress while running, its report as soon as it finishes. */
export function ComparisonColumn({ column, onOpenCitation }: Props) {
  const { run, report, ticker, company } = column
  const lastToolCall = run ? [...run.steps].reverse().find((s) => s.kind === 'tool_call') : undefined

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-gray-800 bg-gray-900/40 p-4">
      <header>
        <h3 className="text-lg font-bold text-gray-100">{ticker}</h3>
        <p className="text-sm text-gray-400">{company}</p>
      </header>

      {run && isActive(run) && (
        <div role="status" className="flex flex-col gap-2 text-sm text-gray-400">
          <p className="flex items-center gap-2">
            <SpinnerIcon /> {run.status === 'finalizing' ? 'Saving…' : 'Researching…'}
          </p>
          {lastToolCall && lastToolCall.kind === 'tool_call' && (
            <p className="truncate text-xs text-gray-500">{summarizeToolCall(lastToolCall.tool, lastToolCall.args).text}</p>
          )}
        </div>
      )}

      {run?.status === 'error' && <ErrorPanel title="Run failed" message={run.error ?? 'Something went wrong.'} />}
      {run?.status === 'cancelled' && <p className="text-sm text-gray-400">Run cancelled.</p>}

      {report && (
        <>
          <VerdictBadge verdict={report.verdict} confidence={report.confidence} />
          <Results report={report} onOpenCitation={onOpenCitation} />
          {run?.reportId && (
            <Link
              to={`/report/${ticker}?id=${run.reportId}`}
              className="text-sm font-medium text-indigo-300 hover:underline focus-visible:outline-2 focus-visible:outline-indigo-400"
            >
              Open full report →
            </Link>
          )}
        </>
      )}
    </div>
  )
}
