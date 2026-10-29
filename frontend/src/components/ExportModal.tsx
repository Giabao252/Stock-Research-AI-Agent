import type { ResearchReport } from '../api/schemas'
import { useDialog } from '../hooks/useDialog'
import { useExport } from '../hooks/useExport'
import { Button } from './Button'
import { CheckIcon, CloseIcon, CopyIcon, PrintIcon, ShareIcon } from './icons'

interface Props {
  open: boolean
  onClose: () => void
  report: ResearchReport
  company: string
  reportId: string | null
}

export function ExportModal({ open, onClose, report, company, reportId }: Props) {
  const panel = useDialog(open, onClose)
  const { shareUrl, markdown, link, copyMarkdown, copyLink, print } = useExport(report, company, reportId)

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center print:hidden">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} aria-hidden="true" />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-title"
        tabIndex={-1}
        className="relative w-full max-w-md rounded-2xl border border-gray-700 bg-gray-950 p-6 shadow-2xl outline-none transition duration-200 starting:translate-y-3 starting:opacity-0"
      >
        <div className="flex items-start justify-between">
          <div>
            <h2 id="export-title" className="text-lg font-semibold text-gray-100">
              Export report
            </h2>
            <p className="mt-1 text-sm text-gray-400">
              {company} ({report.ticker})
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close">
            <CloseIcon />
          </Button>
        </div>

        <div className="mt-6 flex flex-col gap-3">
          <Button onClick={copyMarkdown} className="justify-start">
            {markdown.copied ? <CheckIcon className="text-emerald-300" /> : <CopyIcon />}
            {markdown.copied ? 'Copied!' : markdown.failed ? 'Copy failed — try again' : 'Copy as Markdown'}
          </Button>

          <Button onClick={print} className="justify-start">
            <PrintIcon />
            Download as PDF
          </Button>

          <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-3">
            <p className="flex items-center gap-2 text-sm font-medium text-gray-200">
              <ShareIcon /> Share link
            </p>
            {shareUrl ? (
              <>
                <p className="mt-2 break-all rounded-md bg-gray-950 px-3 py-2 text-xs text-gray-400">{shareUrl}</p>
                <Button size="sm" className="mt-3" onClick={copyLink}>
                  {link.copied ? <CheckIcon className="text-emerald-300" /> : <CopyIcon />}
                  {link.copied ? 'Copied!' : link.failed ? 'Copy failed' : 'Copy link'}
                </Button>
                <p className="mt-2 text-xs text-gray-500">Anyone with this link can view the report (read-only).</p>
              </>
            ) : (
              <p className="mt-2 text-xs text-gray-500">The link is available once the report has been saved.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
