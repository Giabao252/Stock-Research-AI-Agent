import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, ButtonLink } from '../components/Button'
import { CitationDrawer } from '../components/CitationDrawer'
import { ExportModal } from '../components/ExportModal'
import { FollowUpThread } from '../components/FollowUpThread'
import { RefreshIcon, ShareIcon } from '../components/icons'
import { MetricsHeader } from '../components/MetricsHeader'
import { PromptField } from '../components/PromptField'
import { ReasoningChain } from '../components/ReasoningChain'
import { ReasoningToggle } from '../components/ReasoningToggle'
import { ReportDisplay } from '../components/ReportDisplay'
import { RunProgress } from '../components/RunProgress'
import { Banner, ErrorPanel, Skeleton } from '../components/states'
import { useCitationDrawer } from '../hooks/useCitationDrawer'
import { useReportScreen } from '../hooks/useReportScreen'
import { useThread } from '../hooks/useThread'
import { extractMetrics } from '../lib/metrics'

export default function Report() {
  const screen = useReportScreen()
  const thread = useThread(screen.threadKey, screen.ticker)
  const drawer = useCitationDrawer()
  const [exportOpen, setExportOpen] = useState(false)

  const { report, phase } = screen
  const metrics = useMemo(() => (report ? extractMetrics(report.metrics) : null), [report])

  if (phase === 'error') {
    return (
      <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6">
        <ErrorPanel
          title={screen.isSaved ? 'Couldn’t open this report' : 'The analysis didn’t finish'}
          message={screen.error ?? 'Something went wrong.'}
          action={
            <>
              <Button variant="primary" onClick={screen.isSaved ? screen.reloadSaved : screen.retry}>
                <RefreshIcon /> {screen.isSaved ? 'Try again' : 'Retry'}
              </Button>
              <ButtonLink to="/">Back to search</ButtonLink>
            </>
          }
        />
      </main>
    )
  }

  const active = phase === 'starting' || phase === 'streaming' || phase === 'finalizing'

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-6 sm:px-6">
      <div className="flex items-center justify-between gap-3 print:hidden">
        <Link to="/history" className="text-sm text-gray-400 hover:text-gray-200 focus-visible:outline-2 focus-visible:outline-indigo-400">
          ← History
        </Link>
        {phase === 'done' && (
          <div className="flex gap-2">
            <Button size="sm" onClick={screen.retry}>
              <RefreshIcon /> Re-run
            </Button>
            <Button size="sm" variant="primary" onClick={() => setExportOpen(true)}>
              <ShareIcon /> Export
            </Button>
          </div>
        )}
      </div>

      <MetricsHeader ticker={screen.ticker} company={screen.company} metrics={metrics} loading={phase === 'loading' || active} />

      {phase === 'loading' && (
        <div className="flex flex-col gap-4" role="status" aria-label="Loading report">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      )}

      {active && (
        <>
          <RunProgress startedAt={screen.startedAt} finalizing={phase === 'finalizing'} onCancel={screen.cancel} />
          <section aria-labelledby="chain-heading" className="rounded-2xl border border-gray-800 bg-gray-900/40 p-5 print:hidden">
            <h2 id="chain-heading" className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-400">
              Live reasoning
            </h2>
            <ReasoningChain steps={screen.steps} live={phase !== 'finalizing'} />
          </section>
        </>
      )}

      {phase === 'cancelled' && (
        <>
          <Banner tone="warning" title="Run cancelled">
            No report was saved — only finished runs are stored. Here is what the agent had done so far.
          </Banner>
          <ReasoningToggle steps={screen.steps} />
          <div>
            <Button variant="primary" onClick={screen.retry}>
              <RefreshIcon /> Run again
            </Button>
          </div>
        </>
      )}

      {phase === 'done' && report && (
        <>
          <ReasoningToggle steps={screen.steps} />
          <ReportDisplay report={report} onOpenCitation={drawer.open} />

          <section className="flex flex-col gap-5 border-t border-gray-800 pt-6" aria-label="Follow-up questions">
            <FollowUpThread followUps={thread.followUps} onOpenCitation={drawer.open} onRetry={thread.submit} />
            <PromptField
              placeholder={`Ask a follow-up question about ${screen.ticker}…`}
              onSubmit={thread.submit}
              busy={thread.isAsking}
              initialValue={screen.prefill ?? ''}
            />
          </section>

          <ExportModal
            open={exportOpen}
            onClose={() => setExportOpen(false)}
            report={report}
            company={screen.company}
            reportId={screen.reportId}
          />
        </>
      )}

      <CitationDrawer citation={drawer.citation} open={drawer.isOpen} onClose={drawer.close} />
    </main>
  )
}
