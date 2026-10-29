import { useEffect, useState } from 'react'

export type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error }

interface Settled<T> {
  load: () => Promise<T>
  nonce: number
  result: AsyncState<T>
}

const IDLE: AsyncState<never> = { status: 'idle' }
const LOADING: AsyncState<never> = { status: 'loading' }

function toError(value: unknown): Error {
  return value instanceof Error ? value : new Error(String(value))
}

/**
 * Runs `load` whenever its identity changes (memoise it with useCallback) and exposes
 * idle/loading/success/error. Pass `null` to skip. `reload` forces a refetch.
 */
export function useAsync<T>(load: (() => Promise<T>) | null): AsyncState<T> & { reload: () => void } {
  const [nonce, setNonce] = useState(0)
  const [settled, setSettled] = useState<Settled<T> | null>(null)

  useEffect(() => {
    if (!load) return
    let cancelled = false
    load().then(
      (data) => {
        if (!cancelled) setSettled({ load, nonce, result: { status: 'success', data } })
      },
      (error: unknown) => {
        if (!cancelled) setSettled({ load, nonce, result: { status: 'error', error: toError(error) } })
      },
    )
    return () => {
      cancelled = true
    }
  }, [load, nonce])

  const reload = () => setNonce((n) => n + 1)
  if (!load) return { ...IDLE, reload }
  if (settled && settled.load === load && settled.nonce === nonce) return { ...settled.result, reload }
  return { ...LOADING, reload }
}
