import type { Claim } from '../api/schemas'
import type { CitationIndex } from '../lib/citations'
import { hostnameOf, safeHttpUrl } from '../lib/url'
import { ExternalLinkIcon } from './icons'

interface Props {
  citations: CitationIndex
  onOpenCitation: (claim: Claim, number: number) => void
}

export function SourcesList({ citations, onOpenCitation }: Props) {
  if (citations.sources.length === 0) return null

  return (
    <section aria-labelledby="sources-heading">
      <h2 id="sources-heading" className="text-sm font-semibold uppercase tracking-wide text-gray-400">
        Sources
      </h2>
      <ol className="mt-3 flex flex-col gap-2">
        {citations.sources.map(({ number, claim }) => {
          const url = safeHttpUrl(claim.source_url)
          return (
            <li key={number} className="flex items-baseline gap-3 text-sm">
              <span className="w-6 shrink-0 text-right font-semibold tabular-nums text-gray-500">{number}.</span>
              <div className="min-w-0">
                {url ? (
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex max-w-full items-center gap-1.5 text-indigo-300 hover:underline focus-visible:outline-2 focus-visible:outline-indigo-400"
                  >
                    <span className="truncate">{claim.doc_name}</span>
                    <ExternalLinkIcon className="h-3 w-3 shrink-0" />
                  </a>
                ) : (
                  <span className="text-gray-300">{claim.doc_name}</span>
                )}
                <span className="ml-2 text-xs text-gray-500">{hostnameOf(claim.source_url)}</span>
                {claim.chunk_id && (
                  <button
                    type="button"
                    onClick={() => onOpenCitation(claim, number)}
                    className="ml-3 text-xs text-gray-400 underline-offset-2 hover:text-gray-200 hover:underline focus-visible:outline-2 focus-visible:outline-indigo-400 print:hidden"
                  >
                    View passage
                  </button>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
