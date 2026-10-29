import type { Claim } from '../api/schemas'
import type { FollowUp } from '../hooks/threadStore'
import { useCitations } from '../hooks/useCitations'
import { Button } from './Button'
import { CitationMarker } from './CitationMarker'
import { SpinnerIcon } from './icons'

interface AnswerProps {
  followUp: FollowUp
  onOpenCitation: (claim: Claim, number: number) => void
  onRetry: (question: string) => void
}

function AnswerCard({ followUp, onOpenCitation, onRetry }: AnswerProps) {
  const citations = useCitations(followUp.answer?.sources ?? [])

  return (
    <li className="flex flex-col gap-3">
      <p className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-500/20 px-4 py-2.5 text-sm text-indigo-50">
        {followUp.question}
      </p>

      {followUp.status === 'pending' && (
        <p className="flex items-center gap-2 text-sm text-gray-400" role="status">
          <SpinnerIcon /> Researching your question…
        </p>
      )}

      {followUp.status === 'error' && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-rose-500/30 bg-rose-500/5 px-4 py-3 text-sm text-rose-100">
          <span className="min-w-0 flex-1 break-words">{followUp.error}</span>
          <Button size="sm" onClick={() => onRetry(followUp.question)}>
            Try again
          </Button>
        </div>
      )}

      {followUp.status === 'done' && followUp.answer && (
        <div className="rounded-2xl rounded-bl-sm border border-gray-800 bg-gray-900/60 px-4 py-3">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-200">{followUp.answer.text}</p>
          {citations.sources.length > 0 && (
            <ul className="mt-3 flex flex-col gap-1.5 border-t border-gray-800 pt-3 text-xs text-gray-400">
              {citations.sources.map(({ number, claim }) => (
                <li key={number} className="flex gap-1">
                  <CitationMarker number={number} onClick={() => onOpenCitation(claim, number)} />
                  <span className="min-w-0 break-words">{claim.doc_name}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </li>
  )
}

interface Props {
  followUps: readonly FollowUp[]
  onOpenCitation: (claim: Claim, number: number) => void
  onRetry: (question: string) => void
}

/** Accumulating follow-up conversation shown beneath the report. */
export function FollowUpThread({ followUps, onOpenCitation, onRetry }: Props) {
  if (followUps.length === 0) return null
  return (
    <ol className="flex flex-col gap-6" aria-label="Follow-up questions and answers">
      {followUps.map((followUp) => (
        <AnswerCard key={followUp.id} followUp={followUp} onOpenCitation={onOpenCitation} onRetry={onRetry} />
      ))}
    </ol>
  )
}
