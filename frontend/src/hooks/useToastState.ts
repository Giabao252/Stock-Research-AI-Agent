import { useCallback, useEffect, useRef, useState } from 'react'

export interface ToastOptions {
  message: string
  actionLabel?: string
  onAction?: () => void
  durationMs?: number
}

export interface ToastItem extends ToastOptions {
  id: number
}

const DEFAULT_DURATION_MS = 4000

export function useToastState() {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const nextId = useRef(1)
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>())

  const dismiss = useCallback((id: number) => {
    const timer = timers.current.get(id)
    if (timer) clearTimeout(timer)
    timers.current.delete(id)
    setToasts((current) => current.filter((t) => t.id !== id))
  }, [])

  const show = useCallback(
    (options: ToastOptions) => {
      const id = nextId.current++
      setToasts((current) => [...current, { ...options, id }])
      timers.current.set(
        id,
        setTimeout(() => dismiss(id), options.durationMs ?? DEFAULT_DURATION_MS),
      )
      return id
    },
    [dismiss],
  )

  useEffect(() => {
    const active = timers.current
    return () => active.forEach((timer) => clearTimeout(timer))
  }, [])

  return { toasts, show, dismiss }
}
