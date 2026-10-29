import type { Claim } from '../api/schemas'

export interface DiffEntry {
  claim: Claim
  status: 'unchanged' | 'removed' | 'added'
}

export interface ClaimDiff {
  older: DiffEntry[]
  newer: DiffEntry[]
}

const SAME_PASSAGE_THRESHOLD = 0.35
const SIMILAR_TEXT_THRESHOLD = 0.55

function words(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/(\d),(\d)/g, '$1$2')
      .match(/\d+(?:\.\d+)?|[a-z]{3,}/g) ?? [],
  )
}

/** Jaccard overlap of the claims' words and figures, 0..1. */
export function similarity(a: string, b: string): number {
  const wa = words(a)
  const wb = words(b)
  if (wa.size === 0 || wb.size === 0) return 0
  let shared = 0
  for (const w of wa) if (wb.has(w)) shared += 1
  return shared / (wa.size + wb.size - shared)
}

function isSameClaim(a: Claim, b: Claim): boolean {
  const score = similarity(a.text, b.text)
  const samePassage = a.chunk_id !== null && a.chunk_id === b.chunk_id
  return score >= (samePassage ? SAME_PASSAGE_THRESHOLD : SIMILAR_TEXT_THRESHOLD)
}

/**
 * Two runs never phrase a claim identically, so "unchanged" means "says the same thing":
 * highly overlapping text, with a lower bar when both cite the same filing passage.
 * Each older claim can match at most one newer claim.
 */
export function diffClaims(older: readonly Claim[], newer: readonly Claim[]): ClaimDiff {
  const matchedOlder = new Set<number>()
  const matchedNewer = new Set<number>()

  const candidates: Array<{ o: number; n: number; score: number }> = []
  older.forEach((o, oi) =>
    newer.forEach((n, ni) => {
      if (isSameClaim(o, n)) candidates.push({ o: oi, n: ni, score: similarity(o.text, n.text) })
    }),
  )
  candidates.sort((a, b) => b.score - a.score)
  for (const { o, n } of candidates) {
    if (matchedOlder.has(o) || matchedNewer.has(n)) continue
    matchedOlder.add(o)
    matchedNewer.add(n)
  }

  return {
    older: older.map((claim, i) => ({ claim, status: matchedOlder.has(i) ? 'unchanged' : 'removed' })),
    newer: newer.map((claim, i) => ({ claim, status: matchedNewer.has(i) ? 'unchanged' : 'added' })),
  }
}
