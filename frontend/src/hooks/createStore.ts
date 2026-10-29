import { useSyncExternalStore } from 'react'

export interface Store<T> {
  get: () => T
  set: (update: (current: T) => T) => void
  subscribe: (listener: () => void) => () => void
}

/**
 * A tiny external store. Agent runs live outside React so navigating between screens
 * never aborts a run that is still streaming.
 */
export function createStore<T>(initial: T): Store<T> {
  let state = initial
  const listeners = new Set<() => void>()
  return {
    get: () => state,
    set: (update) => {
      const next = update(state)
      if (next === state) return
      state = next
      listeners.forEach((listener) => listener())
    },
    subscribe: (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}

/** `select` must return a referentially stable value for unchanged state. */
export function useStore<T, S>(store: Store<T>, select: (state: T) => S): S {
  return useSyncExternalStore(store.subscribe, () => select(store.get()))
}
