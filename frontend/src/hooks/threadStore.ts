import { analyze, ask } from '../api/client'
import type { Answer } from '../api/schemas'
import { createStore } from './createStore'

export interface FollowUp {
  id: string
  question: string
  status: 'pending' | 'done' | 'error'
  answer: Answer | null
  error: string | null
}

export interface Thread {
  ticker: string
  /** /ask needs a live Redis session, but the analysis session is deleted when its run ends. */
  sessionId: string | null
  followUps: readonly FollowUp[]
}

const EMPTY: Thread = { ticker: '', sessionId: null, followUps: [] }

/** Follow-up conversations keyed by run id (or `report:<id>` for a saved report). */
export const threadStore = createStore<Readonly<Record<string, Thread>>>({})

export function getThread(key: string): Thread {
  return threadStore.get()[key] ?? EMPTY
}

function patchThread(key: string, ticker: string, change: (thread: Thread) => Thread): void {
  threadStore.set((all) => ({ ...all, [key]: change(all[key] ?? { ...EMPTY, ticker }) }))
}

function patchFollowUp(key: string, ticker: string, id: string, change: (f: FollowUp) => FollowUp): void {
  patchThread(key, ticker, (thread) => ({
    ...thread,
    followUps: thread.followUps.map((f) => (f.id === id ? change(f) : f)),
  }))
}

export async function askFollowUp(key: string, ticker: string, question: string): Promise<void> {
  const id = crypto.randomUUID()
  patchThread(key, ticker, (thread) => ({
    ...thread,
    followUps: [...thread.followUps, { id, question, status: 'pending', answer: null, error: null }],
  }))

  try {
    let sessionId = getThread(key).sessionId
    if (!sessionId) {
      // A fresh session is created without opening its stream, so no agent run is started.
      sessionId = (await analyze(ticker)).session_id
      const created = sessionId
      patchThread(key, ticker, (thread) => ({ ...thread, sessionId: created }))
    }
    const answer = await ask({ question, ticker, sessionId })
    patchFollowUp(key, ticker, id, (f) => ({ ...f, status: 'done', answer }))
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not get an answer.'
    patchFollowUp(key, ticker, id, (f) => ({ ...f, status: 'error', error: message }))
  }
}
