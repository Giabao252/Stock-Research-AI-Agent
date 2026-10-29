import { useCallback } from 'react'
import { useStore } from './createStore'
import { askFollowUp, threadStore, type FollowUp } from './threadStore'

const NONE: readonly FollowUp[] = []

/** Follow-up Q&A thread for one report (keyed by run id, or `report:<id>` when viewing a saved one). */
export function useThread(key: string | null, ticker: string) {
  const followUps = useStore(threadStore, (all) => (key ? all[key]?.followUps : undefined)) ?? NONE
  const isAsking = followUps.some((f) => f.status === 'pending')

  const submit = useCallback(
    (question: string) => {
      const text = question.trim()
      if (key && text) void askFollowUp(key, ticker, text)
    },
    [key, ticker],
  )
  return { followUps, isAsking, submit }
}
