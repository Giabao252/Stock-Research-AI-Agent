export interface DisplayMetrics {
  price: number | null
  changePercent: number | null
  peRatio: number | null
  marketCap: number | null
  revenueTtm: number | null
  eps: number | null
  beta: number | null
  week52High: number | null
  week52Low: number | null
}

function toNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string' && value.trim() !== '') {
    const n = Number(value)
    return Number.isFinite(n) ? n : null
  }
  return null
}

function first(raw: Record<string, unknown>, keys: string[]): number | null {
  for (const key of keys) {
    const n = toNumber(raw[key])
    if (n !== null) return n
  }
  return null
}

function scaled(raw: Record<string, unknown>, key: string, factor: number): number | null {
  const n = toNumber(raw[key])
  return n === null ? null : n * factor
}

/**
 * `ResearchReport.metrics` is an open dict. Reports produced after the server started owning it
 * carry stock_data_tool's fields (price, pe_ratio, market_cap, …); older reports had keys the
 * model chose itself (current_price, trailing_pe_ratio, market_cap_billions, …). Read both,
 * and never trust a non-numeric value ("unable_to_retrieve").
 */
export function extractMetrics(raw: Record<string, unknown>): DisplayMetrics {
  return {
    price: first(raw, ['price', 'current_price']),
    changePercent: first(raw, ['change_percent']),
    peRatio: first(raw, ['pe_ratio', 'trailing_pe_ratio', 'p_e_ratio']),
    marketCap: first(raw, ['market_cap']) ?? scaled(raw, 'market_cap_billions', 1e9),
    revenueTtm: first(raw, ['revenue_ttm']) ?? scaled(raw, 'revenue_ttm_billions', 1e9),
    eps: first(raw, ['eps', 'earnings_per_share']),
    beta: first(raw, ['beta']),
    week52High: first(raw, ['week_52_high', '52_week_high']),
    week52Low: first(raw, ['week_52_low', '52_week_low']),
  }
}

export function hasAnyMetric(metrics: DisplayMetrics): boolean {
  return Object.values(metrics).some((v) => v !== null)
}
