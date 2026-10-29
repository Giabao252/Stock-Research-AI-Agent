import { useCallback } from 'react'
import { getChunk } from '../api/client'
import type { Chunk } from '../api/schemas'
import { useAsync, type AsyncState } from './useAsync'

/** Raw filing passage behind a citation. Pass null for web-sourced claims (nothing to fetch). */
export function useChunk(chunkId: string | null): AsyncState<Chunk> & { reload: () => void } {
  const load = useCallback(() => getChunk(chunkId ?? ''), [chunkId])
  return useAsync(chunkId ? load : null)
}
