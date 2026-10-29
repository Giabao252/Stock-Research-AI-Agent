import { useCallback, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { ResearchReport } from '../api/schemas'
import { companyName, type Company } from '../lib/companies'
import { detectIntent } from '../lib/intent'
import { cancelRun, isActive, startRun, type Run } from './runStore'
import { useRuns } from './useRuns'
import { useTickerSearch } from './useTickerSearch'

const MIN_TICKERS = 2
const MAX_TICKERS = 3

export interface ComparisonColumn {
  ticker: string
  company: string
  run: Run | undefined
  report: ResearchReport | null
}

/**
 * Multi-ticker comparison. Run ids live in the URL (`?runs=a,b,c`) so the comparison survives
 * navigating away and back while the runs keep streaming in the background store.
 */
export function useMultiCompare() {
  const [search, setSearch] = useSearchParams()
  const allRuns = useRuns()
  const [draft, setDraft] = useState<readonly string[]>([])

  const runIds = useMemo(() => (search.get('runs') ?? '').split(',').filter(Boolean), [search])
  const columns: ComparisonColumn[] = useMemo(
    () =>
      runIds
        .map((id) => allRuns.find((run) => run.id === id))
        .filter((run): run is Run => run !== undefined)
        .map((run) => ({
          ticker: run.ticker,
          company: companyName(run.ticker),
          run,
          report: run.report,
        })),
    [runIds, allRuns],
  )
  const isComparing = columns.length > 0
  const anyActive = columns.some((c) => c.run && isActive(c.run))

  const addTicker = useCallback((ticker: string) => {
    const symbol = ticker.toUpperCase()
    setDraft((current) =>
      current.includes(symbol) || current.length >= MAX_TICKERS ? current : [...current, symbol],
    )
  }, [])

  const removeTicker = useCallback((ticker: string) => setDraft((current) => current.filter((t) => t !== ticker)), [])

  const picker = useTickerSearch({
    onSelectCompany: (company: Company) => addTicker(company.symbol),
    onSubmitText: (text) => {
      const intent = detectIntent(text)
      if (intent.kind === 'ticker') addTicker(intent.ticker)
    },
  })

  const runComparison = useCallback(() => {
    if (draft.length < MIN_TICKERS) return
    const ids = draft.map((ticker) => startRun(ticker)) // all start now, in parallel
    setSearch({ runs: ids.join(',') })
    setDraft([])
  }, [draft, setSearch])

  const reset = useCallback(() => {
    columns.forEach((c) => c.run && cancelRun(c.run.id))
    setSearch({})
  }, [columns, setSearch])

  return {
    picker,
    draft,
    addTicker,
    removeTicker,
    canRun: draft.length >= MIN_TICKERS,
    atMax: draft.length >= MAX_TICKERS,
    runComparison,
    columns,
    isComparing,
    anyActive,
    reset,
  }
}
