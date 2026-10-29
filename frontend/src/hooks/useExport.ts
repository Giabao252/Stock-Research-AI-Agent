import { useCallback, useMemo } from 'react'
import type { ResearchReport } from '../api/schemas'
import { reportToMarkdown } from '../lib/reportMarkdown'
import { useCopy } from './useCopy'

/** Markdown copy, read-only share link and print for the Export modal. */
export function useExport(report: ResearchReport, company: string, reportId: string | null) {
  const markdown = useCopy()
  const link = useCopy()

  // Reports are readable by id, so the "share link" is the saved-report URL — no POST needed.
  const shareUrl = useMemo(
    () => (reportId ? `${window.location.origin}/report/${report.ticker}?id=${reportId}` : null),
    [reportId, report.ticker],
  )

  const copyMarkdown = useCallback(() => markdown.copy(reportToMarkdown(report, company)), [markdown, report, company])
  const copyLink = useCallback(() => (shareUrl ? link.copy(shareUrl) : Promise.resolve()), [link, shareUrl])
  const print = useCallback(() => window.print(), [])

  return { shareUrl, markdown, link, copyMarkdown, copyLink, print }
}
