import { useState } from 'react'
import type { ChainStep } from '../hooks/runStore'
import { ChevronIcon } from './icons'
import { ReasoningChain } from './ReasoningChain'

/** After a run completes the chain collapses behind this toggle — still there to audit. Hidden in print. */
export function ReasoningToggle({ steps }: { steps: readonly ChainStep[] }) {
  const [open, setOpen] = useState(false)
  if (steps.length === 0) return null

  return (
    <section className="rounded-xl border border-gray-800 bg-gray-900/40 print:hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-gray-300 hover:text-white focus-visible:outline-2 focus-visible:outline-indigo-400"
      >
        {open ? 'Hide reasoning' : 'Show reasoning'}
        <span className="flex items-center gap-2 text-xs text-gray-500">
          {steps.length} steps
          <ChevronIcon className={`h-4 w-4 transition-transform motion-reduce:transition-none ${open ? 'rotate-180' : ''}`} />
        </span>
      </button>
      {open && (
        <div className="border-t border-gray-800 px-4 py-4">
          <ReasoningChain steps={steps} live={false} />
        </div>
      )}
    </section>
  )
}
