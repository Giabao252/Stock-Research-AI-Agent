import { useCallback, useState } from 'react'
import type { Claim } from '../api/schemas'

export interface OpenCitation {
  claim: Claim
  number: number
}

/** `citation` is kept after closing so the panel's content doesn't vanish mid slide-out. */
export function useCitationDrawer() {
  const [state, setState] = useState<{ citation: OpenCitation | null; open: boolean }>({
    citation: null,
    open: false,
  })
  const open = useCallback((claim: Claim, number: number) => setState({ citation: { claim, number }, open: true }), [])
  const close = useCallback(() => setState((current) => ({ ...current, open: false })), [])
  return { citation: state.citation, isOpen: state.open, open, close }
}
