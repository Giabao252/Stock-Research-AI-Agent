import { COMPANIES, findCompany, searchCompanies } from './companies'

export type Intent =
  | { kind: 'empty' }
  | { kind: 'ticker'; ticker: string }
  | { kind: 'question'; question: string; ticker: string | null }

const TICKER_PATTERN = /^[A-Z]{1,5}(\.[A-Z])?$/

// "Nvidia", "Apple Inc." → the first word, matched case-sensitively as written ("Nvidia" but not
// "target" in "price target") so common-word company names don't hijack ordinary sentences.
const NAME_KEYS: ReadonlyArray<{ symbol: string; key: string }> = COMPANIES.map((c) => ({
  symbol: c.symbol,
  key: (c.name.split(/[\s,]+/)[0] ?? '').replace(/[^A-Za-z]/g, ''),
})).filter((n) => n.key.length >= 4)

function stripPunctuation(token: string): string {
  return token.replace(/^[^A-Za-z$]+|[^A-Za-z.]+$/g, '')
}

/** Finds the company a free-text question is about, or null. */
export function extractTicker(text: string): string | null {
  const tokens = text.split(/\s+/).map(stripPunctuation).filter(Boolean)

  for (const token of tokens) {
    if (token.startsWith('$')) {
      const symbol = token.slice(1).toUpperCase()
      if (findCompany(symbol)) return symbol
    }
  }
  // Tickers must be typed in ALL CAPS here: "IT", "ON", "ALL" and "A" are also English words.
  for (const token of tokens) {
    if (token.length >= 2 && token === token.toUpperCase() && findCompany(token)) return token
  }
  for (const token of tokens) {
    const hit = NAME_KEYS.find((n) => n.key === token)
    if (hit) return hit.symbol
  }
  return null
}

export function detectIntent(input: string): Intent {
  const text = input.trim()
  if (!text) return { kind: 'empty' }

  if (!/\s/.test(text)) {
    if (TICKER_PATTERN.test(text)) return { kind: 'ticker', ticker: text }

    const upper = text.toUpperCase()
    if (findCompany(upper)) return { kind: 'ticker', ticker: upper }

    // a lone company name such as "apple" or "nvidia"
    const byName = searchCompanies(text, 1)[0]
    if (byName && byName.name.toLowerCase().startsWith(text.toLowerCase())) {
      return { kind: 'ticker', ticker: byName.symbol }
    }
  }
  return { kind: 'question', question: text, ticker: extractTicker(text) }
}
