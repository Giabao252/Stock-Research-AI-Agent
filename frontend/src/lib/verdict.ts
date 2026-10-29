export type Verdict = 'bullish' | 'bearish' | 'neutral'

interface VerdictStyle {
  label: string
  /** colored chip: background + text + ring */
  chip: string
  text: string
  dot: string
}

// Full class strings (not interpolated) so Tailwind's scanner picks them up.
export const VERDICT_STYLES: Record<Verdict, VerdictStyle> = {
  bullish: {
    label: 'Bullish',
    chip: 'bg-emerald-500/10 text-emerald-300 ring-1 ring-inset ring-emerald-500/30',
    text: 'text-emerald-300',
    dot: 'bg-emerald-400',
  },
  bearish: {
    label: 'Bearish',
    chip: 'bg-rose-500/10 text-rose-300 ring-1 ring-inset ring-rose-500/30',
    text: 'text-rose-300',
    dot: 'bg-rose-400',
  },
  neutral: {
    label: 'Neutral',
    chip: 'bg-gray-500/20 text-gray-200 ring-1 ring-inset ring-gray-400/40',
    text: 'text-gray-300',
    dot: 'bg-gray-400',
  },
}
