import { formatConfidence } from '../lib/format'
import { VERDICT_STYLES, type Verdict } from '../lib/verdict'

interface Props {
  verdict: Verdict
  /** 0..1 — when given, shown next to the label */
  confidence?: number
  size?: 'sm' | 'lg'
}

export function VerdictBadge({ verdict, confidence, size = 'sm' }: Props) {
  const style = VERDICT_STYLES[verdict]
  const sizing = size === 'lg' ? 'px-4 py-2 text-base' : 'px-2.5 py-1 text-xs'
  return (
    <span className={`inline-flex items-center gap-2 rounded-full font-semibold ${sizing} ${style.chip}`}>
      <span className={`h-2 w-2 rounded-full ${style.dot}`} aria-hidden="true" />
      {style.label}
      {confidence !== undefined && (
        <span className="font-medium tabular-nums opacity-80">{formatConfidence(confidence)}</span>
      )}
    </span>
  )
}
