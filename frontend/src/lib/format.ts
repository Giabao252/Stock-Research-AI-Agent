const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
const usdCompact = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  notation: 'compact',
  maximumFractionDigits: 2,
})

export function formatPrice(value: number): string {
  return usd.format(value)
}

export function formatCompactUsd(value: number): string {
  return usdCompact.format(value)
}

export function formatRatio(value: number): string {
  return value.toFixed(1)
}

export function formatSignedPercent(value: number): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

/** confidence arrives as 0..1 */
export function formatConfidence(value: number): string {
  return `${Math.round(Math.min(Math.max(value, 0), 1) * 100)}%`
}
