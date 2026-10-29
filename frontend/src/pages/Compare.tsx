import { useState } from 'react'
import { Button } from '../components/Button'
import { CitationDrawer } from '../components/CitationDrawer'
import { ComparisonColumn } from '../components/ComparisonColumn'
import { ComparisonMetrics } from '../components/ComparisonMetrics'
import { CloseIcon, RefreshIcon } from '../components/icons'
import { TickerSearchBox } from '../components/TickerSearchBox'
import { companyName } from '../lib/companies'
import { useCitationDrawer } from '../hooks/useCitationDrawer'
import { useMultiCompare } from '../hooks/useMultiCompare'

const GRID_COLUMNS: Record<number, string> = { 2: 'lg:grid-cols-2', 3: 'lg:grid-cols-3' }

export default function Compare() {
  const compare = useMultiCompare()
  const drawer = useCitationDrawer()
  const [tab, setTab] = useState(0)
  const activeTab = Math.min(tab, Math.max(compare.columns.length - 1, 0))

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-100">Compare companies</h1>
          <p className="mt-1 text-sm text-gray-400">
            Pick 2–3 tickers. Each is researched in parallel and appears as soon as its report is ready.
          </p>
        </div>
        {compare.isComparing && (
          <Button onClick={compare.reset}>
            <RefreshIcon /> {compare.anyActive ? 'Cancel and start over' : 'New comparison'}
          </Button>
        )}
      </header>

      {!compare.isComparing && (
        <section className="flex flex-col gap-4 rounded-2xl border border-gray-800 bg-gray-900/40 p-5" aria-label="Choose tickers">
          <TickerSearchBox
            search={compare.picker}
            label="Add a ticker or company to compare"
            placeholder={compare.atMax ? 'Maximum of 3 tickers selected' : 'Add a ticker or company…'}
            disabled={compare.atMax}
          />

          {compare.draft.length > 0 ? (
            <ul className="flex flex-wrap gap-2" aria-label="Selected tickers">
              {compare.draft.map((ticker) => (
                <li
                  key={ticker}
                  className="flex items-center gap-2 rounded-full border border-indigo-500/40 bg-indigo-500/10 py-1 pl-3 pr-1 text-sm text-indigo-100"
                >
                  <span className="font-semibold">{ticker}</span>
                  <span className="hidden text-indigo-200/70 sm:inline">{companyName(ticker)}</span>
                  <button
                    type="button"
                    onClick={() => compare.removeTicker(ticker)}
                    aria-label={`Remove ${ticker}`}
                    className="rounded-full p-1 hover:bg-indigo-500/30 focus-visible:outline-2 focus-visible:outline-indigo-400"
                  >
                    <CloseIcon className="h-3 w-3" />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">No tickers selected yet.</p>
          )}

          <div className="flex items-center gap-3">
            <Button variant="primary" disabled={!compare.canRun} onClick={compare.runComparison}>
              Run comparison
            </Button>
            {!compare.canRun && <p className="text-xs text-gray-500">Select at least 2 tickers.</p>}
          </div>
        </section>
      )}

      {compare.isComparing && (
        <>
          <ComparisonMetrics columns={compare.columns} />

          <div role="tablist" aria-label="Tickers" className="flex gap-2 lg:hidden">
            {compare.columns.map((column, i) => (
              <button
                key={column.ticker}
                type="button"
                role="tab"
                aria-selected={i === activeTab}
                onClick={() => setTab(i)}
                className={`rounded-lg px-4 py-2 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-indigo-400 ${
                  i === activeTab ? 'bg-indigo-500 text-white' : 'border border-gray-700 bg-gray-900 text-gray-300'
                }`}
              >
                {column.ticker}
              </button>
            ))}
          </div>

          <div className={`grid gap-4 ${GRID_COLUMNS[compare.columns.length] ?? 'lg:grid-cols-2'}`}>
            {compare.columns.map((column, i) => (
              <div key={column.ticker} role="tabpanel" className={i === activeTab ? 'block' : 'hidden lg:block'}>
                <ComparisonColumn column={column} onOpenCitation={drawer.open} />
              </div>
            ))}
          </div>
        </>
      )}

      <CitationDrawer citation={drawer.citation} open={drawer.isOpen} onClose={drawer.close} />
    </main>
  )
}
