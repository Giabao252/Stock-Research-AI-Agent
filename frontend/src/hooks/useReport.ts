import { useCallback } from 'react'
import { getReport } from '../api/client'
import type { ResearchReport } from '../api/schemas'
import { useAsync, type AsyncState } from './useAsync'

/** Fetches a completed report by id (cached across screens). Pass null to skip. */
export function useReport(reportId: string | null): AsyncState<ResearchReport> & { reload: () => void } {
  const load = useCallback(() => getReport(reportId ?? ''), [reportId])
  return useAsync(reportId ? load : null)
}
