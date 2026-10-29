import { TickerSearchBox } from '../components/TickerSearchBox'
import { Banner } from '../components/states'
import { EXAMPLE_TICKERS, useHome } from '../hooks/useHome'

function TickerChip({ ticker, onClick }: { ticker: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full border border-gray-700 bg-gray-900 px-4 py-1.5 text-sm font-medium text-gray-200 transition-colors hover:border-indigo-400 hover:text-white focus-visible:outline-2 focus-visible:outline-indigo-400"
    >
      {ticker}
    </button>
  )
}

export default function Home() {
  const { search, recent, hint, research } = useHome()

  return (
    <main className="mx-auto flex min-h-[75vh] w-full max-w-2xl flex-col items-center justify-center gap-8 px-4 py-12">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight text-gray-100 sm:text-4xl">Research any stock, every claim cited</h1>
        <p className="mx-auto mt-4 max-w-lg text-sm leading-relaxed text-gray-400 sm:text-base">
          An AI agent reads SEC filings, live market data and recent news, then writes a bull-vs-bear report — and shows
          its reasoning as it works.
        </p>
      </div>

      <div className="w-full">
        <TickerSearchBox
          search={search}
          label="Search by ticker, company name, or ask a question"
          placeholder="Try NVDA, Apple, or “Is Tesla overvalued?”"
          large
          autoFocus
        />
        {hint && (
          <div className="mt-3">
            <Banner tone="info" title="Which company?">
              {hint}
            </Banner>
          </div>
        )}
      </div>

      <section className="w-full text-center" aria-labelledby="chips-heading">
        <h2 id="chips-heading" className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          {recent.length > 0 ? 'Recent searches' : 'Try one of these'}
        </h2>
        <div className="mt-3 flex flex-wrap justify-center gap-2">
          {(recent.length > 0 ? recent : EXAMPLE_TICKERS).map((ticker) => (
            <TickerChip key={ticker} ticker={ticker} onClick={() => research(ticker)} />
          ))}
        </div>
      </section>
    </main>
  )
}
