import type { DiffEntry } from '../lib/diffClaims'

const STYLES: Record<DiffEntry['status'], { item: string; label: string | null; labelStyle: string }> = {
  unchanged: { item: 'text-gray-200', label: null, labelStyle: '' },
  removed: {
    item: 'bg-rose-500/10 text-rose-200 line-through decoration-rose-400/60',
    label: 'Removed',
    labelStyle: 'bg-rose-500/20 text-rose-200',
  },
  added: { item: 'bg-emerald-500/10 text-emerald-100', label: 'New', labelStyle: 'bg-emerald-500/20 text-emerald-200' },
}

/** One side of a bull/bear comparison. Colour is never the only cue — changed claims carry a label too. */
export function ClaimDiff({ entries }: { entries: readonly DiffEntry[] }) {
  if (entries.length === 0) return <p className="text-sm text-gray-500">No claims.</p>
  return (
    <ul className="flex flex-col gap-3">
      {entries.map(({ claim, status }, i) => {
        const style = STYLES[status]
        return (
          <li key={i} className={`rounded-lg px-3 py-2 text-sm leading-relaxed ${style.item}`}>
            {style.label && (
              <span className={`mr-2 inline-block rounded px-1.5 py-0.5 text-[0.65rem] font-semibold uppercase no-underline ${style.labelStyle}`}>
                {style.label}
              </span>
            )}
            {claim.text}
          </li>
        )
      })}
    </ul>
  )
}
