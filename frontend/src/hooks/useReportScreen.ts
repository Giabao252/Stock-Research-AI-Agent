import { useCallback, useEffect, useMemo } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import type { ResearchReport } from '../api/schemas'
import { companyName } from '../lib/companies'
import { cancelRun, ensureRun, findRun, startRun, type ChainStep } from './runStore'
import { useReport } from './useReport'
import { useRun } from './useRuns'

export type ReportPhase =
  | 'loading' // saved report being fetched
  | 'starting'
  | 'streaming'
  | 'finalizing'
  | 'done'
  | 'cancelled'
  | 'error'

/** A saved report has no live stream; rebuild the chain from its recorded tool trace. */
function stepsFromTrace(report: ResearchReport | null): ChainStep[] {
  if (!report) return []
  return report.tool_trace.flatMap((call, i): ChainStep[] => [
    { kind: 'tool_call', id: i * 2, tool: call.tool, args: call.args },
    { kind: 'observe', id: i * 2 + 1, summary: call.result_summary },
  ])
}

/**
 * Everything the Report screen needs, for both a live run (`?run=`) and a saved report (`?id=`).
 * Opening /report/:ticker with neither starts a run immediately — there is no "start" button.
 */
export function useReportScreen() {
  const params = useParams()
  const ticker = (params.ticker ?? '').toUpperCase()
  const navigate = useNavigate()
  const [search, setSearch] = useSearchParams()
  const savedId = search.get('id')
  const runParam = search.get('run')
  const prefill = search.get('q')

  const run = useRun(runParam)
  const saved = useReport(savedId)

  const attachRun = useCallback(
    (runId: string) =>
      setSearch(
        (prev) => {
          const next = new URLSearchParams(prev)
          next.set('run', runId)
          return next
        },
        { replace: true },
      ),
    [setSearch],
  )

  // Attach to (or start) the run for this ticker. An unknown `run` param — e.g. after a page
  // reload — starts a fresh run, and ensureRun reuses one already in flight, so React
  // StrictMode's double-invoked effect can't start two paid runs.
  useEffect(() => {
    if (savedId || !ticker) return
    if (runParam && findRun(runParam)) return
    attachRun(ensureRun(ticker))
  }, [savedId, ticker, runParam, attachRun])

  // Re-running never overwrites the report being viewed: it opens a fresh live run beside it.
  const retry = useCallback(() => {
    const runId = startRun(ticker)
    if (savedId) navigate(`/report/${ticker}?run=${runId}`)
    else attachRun(runId)
  }, [attachRun, navigate, savedId, ticker])
  const cancel = useCallback(() => {
    if (runParam) cancelRun(runParam)
  }, [runParam])

  const savedReport = saved.status === 'success' ? saved.data : null
  const report = savedId ? savedReport : (run?.report ?? null)
  const reportId = savedId ?? run?.reportId ?? null

  const phase: ReportPhase = savedId
    ? saved.status === 'success'
      ? 'done'
      : saved.status === 'error'
        ? 'error'
        : 'loading'
    : !run
      ? 'starting'
      : run.status === 'running'
        ? 'streaming'
        : run.status

  const savedSteps = useMemo(() => stepsFromTrace(savedReport), [savedReport])
  const steps = savedId ? savedSteps : (run?.steps ?? [])

  const error = savedId
    ? saved.status === 'error'
      ? saved.error.message
      : null
    : (run?.error ?? null)

  return {
    ticker,
    company: companyName(ticker),
    isSaved: Boolean(savedId),
    phase,
    steps,
    report,
    reportId,
    error,
    startedAt: run?.startedAt ?? null,
    prefill,
    threadKey: savedId ? `report:${savedId}` : runParam,
    cancel,
    retry,
    reloadSaved: saved.reload,
  }
}
