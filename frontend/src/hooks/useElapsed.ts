import { useEffect, useState } from 'react'

/** Whole seconds since `startedAt`, ticking once a second while `active`. */
export function useElapsedSeconds(startedAt: number | null, active: boolean): number {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (!active) return
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [active])

  return startedAt === null ? 0 : Math.max(0, Math.floor((now - startedAt) / 1000))
}
