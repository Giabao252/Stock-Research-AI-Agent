import type { OpenCitation } from '../hooks/useCitationDrawer'
import { useCitationPassage } from '../hooks/useCitationPassage'
import { useDialog } from '../hooks/useDialog'
import { hostnameOf } from '../lib/url'
import { Button } from './Button'
import { CloseIcon, ExternalLinkIcon, SpinnerIcon } from './icons'
import { Banner } from './states'

interface Props {
  citation: OpenCitation | null
  open: boolean
  onClose: () => void
}

/** Right-hand panel on desktop, bottom sheet on mobile. Slides via transforms, so it stays mounted. */
export function CitationDrawer({ citation, open, onClose }: Props) {
  const panel = useDialog(open, onClose)
  const { isFiling, chunk, passage, filingUrl } = useCitationPassage(citation)

  return (
    <div className="print:hidden">
      <div
        onClick={onClose}
        aria-hidden="true"
        className={`fixed inset-0 z-30 bg-black/60 transition-opacity duration-300 motion-reduce:transition-none ${
          open ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
      />
      <aside
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-title"
        tabIndex={-1}
        inert={!open}
        className={`fixed inset-x-0 bottom-0 z-40 flex max-h-[85vh] flex-col rounded-t-2xl border border-gray-700 bg-gray-950 shadow-2xl outline-none transition-transform duration-300 motion-reduce:transition-none sm:inset-y-0 sm:right-0 sm:left-auto sm:max-h-none sm:w-[28rem] sm:rounded-none sm:rounded-l-2xl ${
          open ? 'translate-x-0 translate-y-0' : 'translate-y-full sm:translate-x-full sm:translate-y-0'
        }`}
      >
        <header className="flex items-start justify-between gap-4 border-b border-gray-800 px-5 py-4">
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-wide text-gray-500">Source {citation?.number}</p>
            <h2 id="source-title" className="mt-1 break-words font-semibold text-gray-100">
              {citation?.claim.doc_name}
            </h2>
            {chunk.status === 'success' && (
              <p className="mt-1 text-xs text-gray-500">
                {chunk.data.section} · {chunk.data.year}
              </p>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close source panel">
            <CloseIcon />
          </Button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {citation && (
            <p className="mb-4 rounded-lg bg-gray-900 p-3 text-sm leading-relaxed text-gray-300">
              <span className="mb-1 block text-xs uppercase tracking-wide text-gray-500">Claim</span>
              {citation.claim.text}
            </p>
          )}

          {!isFiling && (
            <Banner tone="info" title="Web source">
              This claim comes from a web search result, not a filing, so there is no stored passage to show.
              Open the link below to read it at the source.
            </Banner>
          )}
          {isFiling && chunk.status === 'loading' && (
            <p className="flex items-center gap-2 text-sm text-gray-400" role="status">
              <SpinnerIcon /> Loading passage…
            </p>
          )}
          {isFiling && chunk.status === 'error' && (
            <div className="flex flex-col items-start gap-3">
              <Banner tone="warning" title="Couldn’t load this passage">
                {chunk.error.message}
              </Banner>
              <Button size="sm" onClick={chunk.reload}>
                Try again
              </Button>
            </div>
          )}
          {passage && (
            <blockquote className="whitespace-pre-wrap break-words rounded-lg border border-gray-800 bg-gray-900/60 p-4 text-sm leading-relaxed text-gray-400">
              {passage.highlighted ? (
                <>
                  {passage.highlighted.before}
                  <mark
                    ref={(el) => el?.scrollIntoView({ block: 'center' })}
                    className="rounded bg-amber-400/25 px-0.5 text-amber-100"
                  >{passage.highlighted.match}</mark>
                  {passage.highlighted.after}
                </>
              ) : (
                passage.text
              )}
            </blockquote>
          )}
          {passage && !passage.highlighted && (
            <p className="mt-2 text-xs text-gray-500">No single sentence stood out, so the full passage is shown.</p>
          )}
        </div>

        {filingUrl && (
          <footer className="border-t border-gray-800 px-5 py-4">
            <a
              href={filingUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm font-medium text-indigo-300 hover:underline focus-visible:outline-2 focus-visible:outline-indigo-400"
            >
              {isFiling ? 'View full filing' : `Open ${hostnameOf(filingUrl)}`}
              <ExternalLinkIcon />
            </a>
          </footer>
        )}
      </aside>
    </div>
  )
}
