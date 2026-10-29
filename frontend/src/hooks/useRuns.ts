import { useMemo } from 'react'
import { useStore } from './createStore'
import { isActive, runStore, type Run } from './runStore'

export function useRun(id: string | null): Run | undefined {
  return useStore(runStore, (runs) => (id ? runs.find((run) => run.id === id) : undefined))
}

export function useRuns(): readonly Run[] {
  return useStore(runStore, (runs) => runs)
}

/** Runs still streaming — drives the nav indicator. */
export function useActiveRuns(): Run[] {
  const runs = useRuns()
  return useMemo(() => runs.filter(isActive), [runs])
}
