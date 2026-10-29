import { formatConfidence } from '../lib/format'
import { VERDICT_STYLES, type Verdict } from '../lib/verdict'

const SEGMENTS = 10

// Whole-class lookups so no width/colour is built from a runtime value (no inline styles).
export function ConfidenceMeter({ value, verdict }: { value: number; verdict: Verdict }) {
  const filled = Math.round(Math.min(Math.max(value, 0), 1) * SEGMENTS)
  return (
    <div className="flex items-center gap-3" role="img" aria-label={`Confidence ${formatConfidence(value)}`}>
      <div className="flex gap-1">
        {Array.from({ length: SEGMENTS }, (_, i) => (
          <span
            key={i}
            className={`h-2 w-3 rounded-sm ${i < filled ? VERDICT_STYLES[verdict].dot : 'bg-gray-800'}`}
          />
        ))}
      </div>
      <span className="text-sm font-medium tabular-nums text-gray-300">{formatConfidence(value)} confidence</span>
    </div>
  )
}
