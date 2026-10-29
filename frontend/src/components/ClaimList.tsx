import type { Claim } from '../api/schemas'
import type { CitationIndex } from '../lib/citations'
import { CitationMarker } from './CitationMarker'

interface Props {
  claims: readonly Claim[]
  citations: CitationIndex
  onOpenCitation: (claim: Claim, number: number) => void
  tone: 'bull' | 'bear'
}

const BULLET = { bull: 'bg-emerald-400', bear: 'bg-rose-400' } as const

export function ClaimList({ claims, citations, onOpenCitation, tone }: Props) {
  if (claims.length === 0) return <p className="text-sm text-gray-500">No claims in this section.</p>

  return (
    <ul className="flex flex-col gap-4">
      {claims.map((claim, i) => {
        const number = citations.numberFor(claim)
        return (
          <li key={i} className="flex gap-3">
            <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${BULLET[tone]}`} aria-hidden="true" />
            <p className="text-sm leading-relaxed text-gray-200">
              {claim.text}
              <CitationMarker number={number} onClick={() => onOpenCitation(claim, number)} />
            </p>
          </li>
        )
      })}
    </ul>
  )
}
