import { useMemo } from 'react'
import { highlightBestPassage, tidyChunkText } from '../lib/highlight'
import { safeHttpUrl } from '../lib/url'
import type { OpenCitation } from './useCitationDrawer'
import { useChunk } from './useChunk'

/** Everything the source drawer shows: the fetched filing passage, with the supporting sentence marked. */
export function useCitationPassage(citation: OpenCitation | null) {
  const chunkId = citation?.claim.chunk_id ?? null
  const chunk = useChunk(chunkId)

  const passage = useMemo(() => {
    if (chunk.status !== 'success' || !citation) return null
    const text = tidyChunkText(chunk.data.text)
    return { text, highlighted: highlightBestPassage(text, citation.claim.text) }
  }, [chunk, citation])

  return {
    isFiling: chunkId !== null,
    chunk,
    passage,
    // For filings the link is the chunk's own EDGAR document; web claims carry their own URL.
    filingUrl: safeHttpUrl(chunk.status === 'success' ? chunk.data.source_url : (citation?.claim.source_url ?? '')),
  }
}
