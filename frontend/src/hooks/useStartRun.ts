import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { startRun } from './runStore'

/** Starts a fresh agent run for a ticker and opens its Report screen. */
export function useStartRun() {
  const navigate = useNavigate()
  return useCallback(
    (ticker: string) => {
      const symbol = ticker.toUpperCase()
      navigate(`/report/${symbol}?run=${startRun(symbol)}`)
    },
    [navigate],
  )
}
