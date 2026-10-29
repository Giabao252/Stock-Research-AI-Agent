import { useMemo } from 'react'
import type { Claim, ResearchReport } from '../api/schemas'
import { buildCitationIndex, type CitationIndex } from '../lib/citations'

/** Citation numbers for a whole report: bull case first, then bear, by order of first use. */
export function useReportCitations(report: ResearchReport): CitationIndex {
  return useMemo(() => buildCitationIndex([...report.bull_case, ...report.bear_case]), [report])
}

export function useCitations(claims: readonly Claim[]): CitationIndex {
  return useMemo(() => buildCitationIndex(claims), [claims])
}
