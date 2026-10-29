import type { ResearchReport } from '../api/schemas'
import { buildCitationIndex } from './citations'
import { formatDateTime } from './dates'
import { formatCompactUsd, formatConfidence, formatPrice, formatRatio } from './format'
import { extractMetrics } from './metrics'
import { safeHttpUrl } from './url'
import { VERDICT_STYLES } from './verdict'

function metricsLines(report: ResearchReport): string[] {
  const m = extractMetrics(report.metrics)
  const lines: string[] = []
  if (m.price !== null) lines.push(`- Price: ${formatPrice(m.price)}`)
  if (m.peRatio !== null) lines.push(`- P/E: ${formatRatio(m.peRatio)}`)
  if (m.marketCap !== null) lines.push(`- Market cap: ${formatCompactUsd(m.marketCap)}`)
  if (m.revenueTtm !== null) lines.push(`- Revenue (TTM): ${formatCompactUsd(m.revenueTtm)}`)
  return lines
}

export function reportToMarkdown(report: ResearchReport, companyName: string): string {
  const claims = [...report.bull_case, ...report.bear_case]
  const index = buildCitationIndex(claims)
  const out: string[] = []

  out.push(`# ${companyName} (${report.ticker}) — Research Report`)
  out.push(`_Generated ${formatDateTime(report.generated_at)}_`)
  out.push(`**Verdict:** ${VERDICT_STYLES[report.verdict].label} · **Confidence:** ${formatConfidence(report.confidence)}`)

  if (report.partial) {
    out.push(`> ⚠️ Partial report${report.partial_reason ? `: ${report.partial_reason}` : ''}`)
  }

  const metrics = metricsLines(report)
  if (metrics.length) out.push(['## Key metrics', ...metrics].join('\n'))

  const section = (title: string, list: ResearchReport['bull_case']) =>
    [`## ${title}`, ...list.map((c) => `- ${c.text} [${index.numberFor(c)}]`)].join('\n')
  out.push(section('Bull case', report.bull_case))
  out.push(section('Bear case', report.bear_case))

  const sources = index.sources.map(({ number, claim }) => {
    const url = safeHttpUrl(claim.source_url)
    return url ? `${number}. [${claim.doc_name}](${url})` : `${number}. ${claim.doc_name}`
  })
  if (sources.length) out.push(['## Sources', ...sources].join('\n'))

  return `${out.join('\n\n')}\n`
}
