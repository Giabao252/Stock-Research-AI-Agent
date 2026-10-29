import { useCallback, useEffect, useRef, useState } from 'react'

const RESET_MS = 2000

/** Copies text and reports `copied` for two seconds (the "Copied!" button label). */
export function useCopy() {
  const [copied, setCopied] = useState(false)
  const [failed, setFailed] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current)
  }, [])

  const copy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setFailed(false)
      setCopied(true)
    } catch {
      setCopied(false)
      setFailed(true)
    }
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => {
      setCopied(false)
      setFailed(false)
    }, RESET_MS)
  }, [])

  return { copied, failed, copy }
}
