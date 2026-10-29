import { useCallback, useRef, useState } from 'react'
import { ApiError, getReport } from '../api/client'
import type { ResearchReport } from '../api/schemas'
import { loadHistoryIndex, removeHistoryEntry } from '../api/storage'
import { useToast } from './toastContext'
import { useAsync } from './useAsync'

export interface HistoryRow {
  reportId: string
  ticker: string
  report: ResearchReport
}

const UNDO_WINDOW_MS = 4000
const MAX_SELECTED = 2

async function loadRows(entries: ReturnType<typeof loadHistoryIndex>) {
  const settled = await Promise.allSettled(entries.map((e) => getReport(e.reportId)))
  const rows: HistoryRow[] = []
  let failed = 0
  settled.forEach((result, i) => {
    const entry = entries[i]
    if (result.status === 'fulfilled') {
      rows.push({ reportId: entry.reportId, ticker: entry.ticker, report: result.value })
    } else if (result.reason instanceof ApiError && result.reason.status === 404) {
      removeHistoryEntry(entry.reportId) // report no longer exists server-side
    } else {
      failed += 1
    }
  })
  rows.sort((a, b) => b.report.generated_at.getTime() - a.report.generated_at.getTime())
  return { rows, failed }
}

export function useHistory() {
  const toast = useToast()
  const [entries] = useState(loadHistoryIndex)
  const load = useCallback(() => loadRows(entries), [entries])
  const state = useAsync(entries.length > 0 ? load : null)

  const [hidden, setHidden] = useState<ReadonlySet<string>>(new Set())
  const [selected, setSelected] = useState<readonly string[]>([])
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>())

  const loaded = state.status === 'success' ? state.data : null
  const rows = (loaded?.rows ?? []).filter((r) => !hidden.has(r.reportId))
  const isLoading = entries.length > 0 && (state.status === 'loading' || state.status === 'idle')

  const toggleSelected = useCallback((reportId: string) => {
    setSelected((current) => {
      if (current.includes(reportId)) return current.filter((id) => id !== reportId)
      return [...current, reportId].slice(-MAX_SELECTED) // a third pick drops the oldest
    })
  }, [])

  // Deletion is only finalised after the undo window, so Undo is just "cancel the timer".
  const requestDelete = useCallback(
    (reportId: string) => {
      setHidden((current) => new Set(current).add(reportId))
      setSelected((current) => current.filter((id) => id !== reportId))

      const restore = () => {
        const timer = timers.current.get(reportId)
        if (timer) clearTimeout(timer)
        timers.current.delete(reportId)
        setHidden((current) => {
          const next = new Set(current)
          next.delete(reportId)
          return next
        })
      }
      timers.current.set(
        reportId,
        setTimeout(() => {
          timers.current.delete(reportId)
          removeHistoryEntry(reportId)
        }, UNDO_WINDOW_MS),
      )
      toast.show({
        message: 'Report deleted',
        actionLabel: 'Undo',
        onAction: restore,
        durationMs: UNDO_WINDOW_MS,
      })
    },
    [toast],
  )

  const selectedRows = selected
    .map((id) => rows.find((r) => r.reportId === id))
    .filter((r): r is HistoryRow => r !== undefined)
  const sameTicker = selectedRows.length === MAX_SELECTED && selectedRows[0].ticker === selectedRows[1].ticker

  return {
    rows,
    isLoading,
    error: state.status === 'error' ? state.error.message : null,
    failedCount: loaded?.failed ?? 0,
    retry: state.reload,
    selected,
    toggleSelected,
    requestDelete,
    canCompare: sameTicker,
    compareHint:
      selected.length === MAX_SELECTED && !sameTicker ? 'Pick two reports for the same ticker to compare them.' : null,
    compareIds: selectedRows.map((r) => r.reportId),
  }
}
