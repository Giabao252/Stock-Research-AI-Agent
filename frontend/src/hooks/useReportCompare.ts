import { useCallback, useMemo } from 'react'
import { getReport } from '../api/client'
import { diffClaims } from '../lib/diffClaims'
import { useAsync } from './useAsync'

/** Loads two saved reports, orders them old → new, and diffs their claims. */
export function useReportCompare(idA: string, idB: string) {
  const load = useCallback(async () => {
    const [a, b] = await Promise.all([getReport(idA), getReport(idB)])
    const [older, newer] = a.generated_at <= b.generated_at ? [a, b] : [b, a]
    return {
      older,
      newer,
      olderId: a === older ? idA : idB,
      newerId: a === older ? idB : idA,
    }
  }, [idA, idB])
  const state = useAsync(load)

  const comparison = useMemo(() => {
    if (state.status !== 'success') return null
    const { older, newer } = state.data
    return {
      ...state.data,
      bull: diffClaims(older.bull_case, newer.bull_case),
      bear: diffClaims(older.bear_case, newer.bear_case),
      verdictChanged: older.verdict !== newer.verdict,
      confidenceDelta: newer.confidence - older.confidence,
      sameTicker: older.ticker === newer.ticker,
    }
  }, [state])

  return {
    status: state.status,
    error: state.status === 'error' ? state.error.message : null,
    comparison,
    reload: state.reload,
  }
}
