export interface HighlightedPassage {
  before: string
  match: string
  after: string
}

const MAX_SEGMENT = 200
const WINDOW = 90
const MIN_SCORE = 2

function tokens(text: string): string[] {
  return (
    text
      .toLowerCase()
      .replace(/(\d),(\d)/g, '$1$2') // 215,938 → 215938
      .match(/\d+(?:\.\d+)?|[a-z]{4,}/g) ?? []
  )
}

interface Segment {
  start: number
  end: number
}

/** Sentences first; anything still long (tables, run-on text) is re-cut along line breaks. */
function segment(text: string): Segment[] {
  const sentences: Segment[] = []
  const sentenceEnd = /[.!?]+(?=\s|$)/g
  let start = 0
  for (let m = sentenceEnd.exec(text); m; m = sentenceEnd.exec(text)) {
    sentences.push({ start, end: m.index + m[0].length })
    start = m.index + m[0].length
  }
  if (start < text.length) sentences.push({ start, end: text.length })

  const result: Segment[] = []
  for (const s of sentences) {
    if (s.end - s.start <= MAX_SEGMENT) {
      result.push(s)
      continue
    }
    let windowStart = s.start
    const lineBreak = /\n/g
    lineBreak.lastIndex = s.start
    for (let m = lineBreak.exec(text); m && m.index < s.end; m = lineBreak.exec(text)) {
      if (m.index - windowStart >= WINDOW) {
        result.push({ start: windowStart, end: m.index })
        windowStart = m.index
      }
    }
    result.push({ start: windowStart, end: s.end })
  }
  return result.filter((s) => text.slice(s.start, s.end).trim().length > 0)
}

/**
 * The backend returns a whole chunk, not the supporting sentence, so pick the sentence that
 * shares the most numbers/keywords with the claim. Returns null when nothing matches well.
 */
export function highlightBestPassage(chunkText: string, claimText: string): HighlightedPassage | null {
  const claimTokens = new Set(tokens(claimText))
  if (claimTokens.size === 0) return null

  let best: { segment: Segment; score: number } | null = null
  for (const seg of segment(chunkText)) {
    let score = 0
    for (const token of new Set(tokens(chunkText.slice(seg.start, seg.end)))) {
      if (claimTokens.has(token)) score += /^\d/.test(token) ? 2 : 1 // figures are stronger evidence
    }
    if (!best || score > best.score) best = { segment: seg, score }
  }
  if (!best || best.score < MIN_SCORE) return null

  const { start, end } = best.segment
  const raw = chunkText.slice(start, end)
  const lead = raw.length - raw.trimStart().length
  const matchStart = start + lead
  const matchEnd = start + raw.trimEnd().length
  return {
    before: chunkText.slice(0, matchStart),
    match: chunkText.slice(matchStart, matchEnd),
    after: chunkText.slice(matchEnd),
  }
}

/** Chunk text is extracted from HTML tables, so it is full of one-cell-per-line breaks. */
export function tidyChunkText(text: string): string {
  return text.replace(/\n{3,}/g, '\n\n').trim()
}
