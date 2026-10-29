import { z } from 'zod'
import raw from '../data/sp500.json'

const companySchema = z.object({ symbol: z.string(), name: z.string() })
export type Company = z.infer<typeof companySchema>

// Static S&P 500 list bundled at build time; validated once so a bad regeneration fails loudly.
export const COMPANIES: readonly Company[] = z.array(companySchema).parse(raw)

const BY_SYMBOL = new Map(COMPANIES.map((c) => [c.symbol, c]))

export function findCompany(ticker: string): Company | undefined {
  return BY_SYMBOL.get(ticker.toUpperCase())
}

export function companyName(ticker: string): string {
  return findCompany(ticker)?.name ?? ticker.toUpperCase()
}

// Tie-break for equally good matches ("micro" → Microsoft before Micron): well-known names first.
const POPULAR = [
  'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'GOOG', 'META', 'TSLA', 'BRK.B', 'AVGO', 'LLY', 'JPM',
  'V', 'XOM', 'UNH', 'MA', 'COST', 'HD', 'PG', 'NFLX', 'JNJ', 'BAC', 'ORCL', 'CRM', 'AMD', 'KO',
  'PEP', 'DIS', 'INTC', 'WMT',
]
const POPULARITY = new Map(POPULAR.map((symbol, i) => [symbol, i]))

function popularity(symbol: string): number {
  return POPULARITY.get(symbol) ?? POPULAR.length
}

function rank(company: Company, q: string): number {
  const symbol = company.symbol.toLowerCase()
  const name = company.name.toLowerCase()
  if (symbol === q) return 0

  // Short queries are usually tickers; from three characters on people are typing a name.
  const symbolPrefix = symbol.startsWith(q)
  const namePrefix = name.startsWith(q)
  if (q.length >= 3) {
    if (namePrefix) return 1
    if (symbolPrefix) return 2
  } else {
    if (symbolPrefix) return 1
    if (namePrefix) return 2
  }
  if (name.split(/[\s,.-]+/).some((word) => word.startsWith(q))) return 3
  if (symbol.includes(q)) return 4
  if (name.includes(q)) return 5
  return -1
}

/** Matches ticker symbol and company name simultaneously, best match first. */
export function searchCompanies(query: string, limit = 8): Company[] {
  const q = query.trim().toLowerCase()
  if (!q) return []

  const scored: Array<{ company: Company; score: number }> = []
  for (const company of COMPANIES) {
    const score = rank(company, q)
    if (score >= 0) scored.push({ company, score })
  }
  scored.sort(
    (a, b) =>
      a.score - b.score ||
      popularity(a.company.symbol) - popularity(b.company.symbol) ||
      a.company.name.localeCompare(b.company.name),
  )
  return scored.slice(0, limit).map((s) => s.company)
}
