import type { Claim, ResearchReport } from '../api/schemas'
import { useReportCitations } from '../hooks/useCitations'
import { formatDateTime } from '../lib/dates'
import { Banner } from './states'
import { ClaimList } from './ClaimList'
import { ConfidenceMeter } from './ConfidenceMeter'
import { SourcesList } from './SourcesList'
import { VerdictBadge } from './VerdictBadge'

interface Props {
  report: ResearchReport
  onOpenCitation: (claim: Claim, number: number) => void
}

export function ReportDisplay({ report, onOpenCitation }: Props) {
  const citations = useReportCitations(report)

  return (
    <article className="flex flex-col gap-8">
      {report.partial && (
        <Banner tone="warning" title="This is a partial report">
          {report.partial_reason ?? 'Some evidence could not be gathered or verified, so treat the conclusions with care.'}
        </Banner>
      )}

      <section className="flex flex-col gap-4 rounded-2xl border border-gray-800 bg-gray-900/50 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3">
          <p className="text-xs uppercase tracking-wide text-gray-500">Verdict</p>
          <VerdictBadge verdict={report.verdict} size="lg" />
        </div>
        <div className="flex flex-col gap-2 sm:items-end">
          <ConfidenceMeter value={report.confidence} verdict={report.verdict} />
          <p className="text-xs text-gray-500">Generated {formatDateTime(report.generated_at)}</p>
        </div>
      </section>

      <div className="grid gap-8 md:grid-cols-2">
        <section aria-labelledby="bull-heading">
          <h2 id="bull-heading" className="mb-4 flex items-center gap-2 text-lg font-semibold text-emerald-300">
            Bull case
            <span className="text-sm font-normal text-gray-500">{report.bull_case.length}</span>
          </h2>
          <ClaimList claims={report.bull_case} citations={citations} onOpenCitation={onOpenCitation} tone="bull" />
        </section>
        <section aria-labelledby="bear-heading">
          <h2 id="bear-heading" className="mb-4 flex items-center gap-2 text-lg font-semibold text-rose-300">
            Bear case
            <span className="text-sm font-normal text-gray-500">{report.bear_case.length}</span>
          </h2>
          <ClaimList claims={report.bear_case} citations={citations} onOpenCitation={onOpenCitation} tone="bear" />
        </section>
      </div>

      <SourcesList citations={citations} onOpenCitation={onOpenCitation} />
    </article>
  )
}
