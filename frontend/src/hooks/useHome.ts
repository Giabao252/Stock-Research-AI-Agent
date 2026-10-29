import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loadRecentTickers } from '../api/storage'
import type { Company } from '../lib/companies'
import { detectIntent } from '../lib/intent'
import { startRun } from './runStore'
import { useTickerSearch } from './useTickerSearch'

export const EXAMPLE_TICKERS = ['NVDA', 'AAPL', 'MSFT', 'TSLA', 'AMZN'] as const

const NO_COMPANY_HINT =
  'I couldn’t tell which company that’s about. Include a ticker or company name — e.g. “Is NVDA overvalued?”'

/** Home screen: turns whatever was typed or clicked into a started run + navigation. */
export function useHome() {
  const navigate = useNavigate()
  const [recent] = useState(loadRecentTickers)
  const [hint, setHint] = useState<string | null>(null)

  const research = useCallback(
    (ticker: string, question?: string) => {
      setHint(null)
      const runId = startRun(ticker)
      const params = new URLSearchParams({ run: runId })
      if (question) params.set('q', question) // pre-fills the follow-up box once the report is ready
      navigate(`/report/${ticker}?${params.toString()}`)
    },
    [navigate],
  )

  const onSubmitText = useCallback(
    (text: string) => {
      const intent = detectIntent(text)
      if (intent.kind === 'ticker') research(intent.ticker)
      else if (intent.kind === 'question') {
        if (intent.ticker) research(intent.ticker, intent.question)
        else setHint(NO_COMPANY_HINT)
      }
    },
    [research],
  )

  const search = useTickerSearch({
    onSelectCompany: (company: Company) => research(company.symbol),
    onSubmitText,
  })

  // Typing again dismisses a stale "couldn't tell which company" hint.
  const searchWithHintReset: typeof search = {
    ...search,
    onChange: (event) => {
      setHint(null)
      search.onChange(event)
    },
  }

  return { search: searchWithHintReset, recent, hint, research }
}
