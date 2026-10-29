import type { Claim } from '../api/schemas'

export interface CitationSource {
  number: number
  /** The first claim that cited this source — used for the label and passage highlighting. */
  claim: Claim
}

export interface CitationIndex {
  sources: CitationSource[]
  numberFor: (claim: Claim) => number
}

/** A filing claim is identified by its chunk; a web claim by its URL. */
export function citationKey(claim: Claim): string {
  return claim.chunk_id ? `chunk:${claim.chunk_id}` : `url:${claim.source_url}`
}

/** Numbers sources 1..n in order of first appearance, so repeated citations share a number. */
export function buildCitationIndex(claims: readonly Claim[]): CitationIndex {
  const numbers = new Map<string, number>()
  const sources: CitationSource[] = []

  for (const claim of claims) {
    const key = citationKey(claim)
    if (!numbers.has(key)) {
      numbers.set(key, sources.length + 1)
      sources.push({ number: sources.length + 1, claim })
    }
  }
  return { sources, numberFor: (claim) => numbers.get(citationKey(claim)) ?? 0 }
}
