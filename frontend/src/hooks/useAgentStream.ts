import { useCallback } from 'react'
import { cancelRun, isActive } from './runStore'
import { useRun } from './useRuns'

/** Live state of one agent run (steps, status, report) plus a cancel action. */
export function useAgentStream(runId: string | null) {
  const run = useRun(runId)
  const cancel = useCallback(() => {
    if (runId) cancelRun(runId)
  }, [runId])
  return { run, isActive: run ? isActive(run) : false, cancel }
}
