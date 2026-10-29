import { analyze, ApiError, getReport, isAbortError, deleteSession } from '../api/client'
import type { ResearchReport } from '../api/schemas'
import { streamSession } from '../api/stream'
import { addHistoryEntry, pushRecentTicker } from '../api/storage'
import { createStore } from './createStore'

export type RunStatus = 'starting' | 'running' | 'finalizing' | 'done' | 'error' | 'cancelled'

export type ChainStep =
  | { kind: 'thought'; id: number; content: string }
  | { kind: 'tool_call'; id: number; tool: string; args: Record<string, unknown> }
  | { kind: 'observe'; id: number; summary: string }

export interface Run {
  id: string
  ticker: string
  status: RunStatus
  steps: readonly ChainStep[]
  reportId: string | null
  report: ResearchReport | null
  error: string | null
  startedAt: number
  endedAt: number | null
}

export const runStore = createStore<readonly Run[]>([])

const controllers = new Map<string, AbortController>()
const sessionIds = new Map<string, string>()

export function isActive(run: Pick<Run, 'status'>): boolean {
  return run.status === 'starting' || run.status === 'running' || run.status === 'finalizing'
}

function patch(id: string, change: (run: Run) => Run): void {
  runStore.set((runs) => runs.map((run) => (run.id === id ? change(run) : run)))
}

function finish(id: string, status: 'done' | 'error' | 'cancelled', extra: Partial<Run> = {}): void {
  patch(id, (run) => ({ ...run, ...extra, status, endedAt: Date.now() }))
}

export function findRun(id: string): Run | undefined {
  return runStore.get().find((run) => run.id === id)
}

/** The run to attach to for a ticker if one is already in flight (guards against double-starts). */
export function findActiveRun(ticker: string): Run | undefined {
  return runStore.get().find((run) => run.ticker === ticker && isActive(run))
}

export function startRun(rawTicker: string): string {
  const ticker = rawTicker.trim().toUpperCase()
  const id = crypto.randomUUID()
  const run: Run = {
    id,
    ticker,
    status: 'starting',
    steps: [],
    reportId: null,
    report: null,
    error: null,
    startedAt: Date.now(),
    endedAt: null,
  }
  runStore.set((runs) => [...runs, run])
  pushRecentTicker(ticker)
  void execute(id, ticker)
  return id
}

export function ensureRun(ticker: string): string {
  return findActiveRun(ticker.toUpperCase())?.id ?? startRun(ticker)
}

export function cancelRun(id: string): void {
  const run = findRun(id)
  if (!run || !isActive(run)) return
  controllers.get(id)?.abort()
  finish(id, 'cancelled')
  // Fire-and-forget: frees the Redis session so nothing lingers on the free tier.
  const sessionId = sessionIds.get(id)
  if (sessionId) void deleteSession(sessionId)
}

// Persisting the report is the last thing the server does after the `done` event, so the
// first fetch can race it; retry briefly before giving up.
async function fetchReportWithRetry(reportId: string): Promise<ResearchReport> {
  const delays = [0, 600, 1500, 3000]
  let lastError: unknown
  for (const delay of delays) {
    if (delay) await new Promise((resolve) => setTimeout(resolve, delay))
    try {
      return await getReport(reportId)
    } catch (error) {
      lastError = error
      if (!(error instanceof ApiError) || error.status !== 404) throw error
    }
  }
  throw lastError
}

async function execute(id: string, ticker: string): Promise<void> {
  const controller = new AbortController()
  controllers.set(id, controller)
  let stepId = 0

  try {
    const { session_id } = await analyze(ticker, controller.signal)
    sessionIds.set(id, session_id)
    patch(id, (run) => ({ ...run, status: 'running' }))

    await streamSession(session_id, controller.signal, (event) => {
      switch (event.type) {
        case 'thought':
          patch(id, (run) => ({ ...run, steps: [...run.steps, { kind: 'thought', id: stepId++, content: event.content }] }))
          break
        case 'tool_call':
          patch(id, (run) => ({
            ...run,
            steps: [...run.steps, { kind: 'tool_call', id: stepId++, tool: event.tool, args: event.args }],
          }))
          break
        case 'observe':
          patch(id, (run) => ({ ...run, steps: [...run.steps, { kind: 'observe', id: stepId++, summary: event.summary }] }))
          break
        case 'done':
          patch(id, (run) => ({ ...run, status: 'finalizing', reportId: event.report_id }))
          break
        case 'error':
          finish(id, 'error', { error: event.message })
          break
        default: {
          const unreachable: never = event
          void unreachable
        }
      }
    })

    const run = findRun(id)
    if (!run || run.status === 'cancelled' || run.status === 'error') return
    if (!run.reportId) {
      finish(id, 'error', { error: 'The connection closed before the report was finished. Please try again.' })
      return
    }

    const report = await fetchReportWithRetry(run.reportId)
    addHistoryEntry({ reportId: run.reportId, ticker })
    finish(id, 'done', { report })
  } catch (error) {
    if (isAbortError(error)) return // cancelRun already set the status
    const run = findRun(id)
    if (run?.status === 'cancelled') return
    finish(id, 'error', { error: error instanceof Error ? error.message : 'Something went wrong.' })
  } finally {
    controllers.delete(id)
    sessionIds.delete(id)
  }
}
