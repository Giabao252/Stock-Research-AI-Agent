import type { ChainStep } from '../hooks/runStore'
import { useAutoScroll } from '../hooks/useAutoScroll'
import { isFailureSummary, summarizeToolCall, type ToolKind } from '../lib/toolSummary'
import { AlertIcon, CalcIcon, CheckIcon, ChartIcon, FilingIcon, GlobeIcon, SparkIcon } from './icons'

const TOOL_STYLES: Record<ToolKind, { chip: string; Icon: typeof FilingIcon }> = {
  filings: { chip: 'border-indigo-500/30 bg-indigo-500/10 text-indigo-200', Icon: FilingIcon },
  market: { chip: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200', Icon: ChartIcon },
  web: { chip: 'border-sky-500/30 bg-sky-500/10 text-sky-200', Icon: GlobeIcon },
  edgar: { chip: 'border-violet-500/30 bg-violet-500/10 text-violet-200', Icon: FilingIcon },
  calc: { chip: 'border-amber-500/30 bg-amber-500/10 text-amber-200', Icon: CalcIcon },
  system: { chip: 'border-gray-700 bg-gray-800/60 text-gray-300', Icon: SparkIcon },
}

// Each step eases in as it arrives over SSE.
const ENTER = 'transition duration-300 motion-reduce:transition-none starting:translate-y-2 starting:opacity-0'

function Step({ step }: { step: ChainStep }) {
  switch (step.kind) {
    case 'thought':
      return (
        <li className={`border-l-2 border-gray-700 pl-4 text-sm leading-relaxed text-gray-300 ${ENTER}`}>
          <p className="whitespace-pre-wrap">{step.content}</p>
        </li>
      )
    case 'tool_call': {
      const { kind, text } = summarizeToolCall(step.tool, step.args)
      const { chip, Icon } = TOOL_STYLES[kind]
      return (
        <li className={ENTER}>
          <span className={`inline-flex max-w-full items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${chip}`}>
            <Icon className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{text}</span>
          </span>
        </li>
      )
    }
    case 'observe': {
      const failed = isFailureSummary(step.summary)
      return (
        <li className={`flex items-start gap-2 pl-4 text-xs ${failed ? 'text-amber-300' : 'text-gray-500'} ${ENTER}`}>
          {failed ? <AlertIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" /> : <CheckIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />}
          <span className="break-words">{step.summary}</span>
        </li>
      )
    }
  }
}

interface Props {
  steps: readonly ChainStep[]
  /** true while the run is still streaming — shows the working indicator and follows new steps */
  live: boolean
}

export function ReasoningChain({ steps, live }: Props) {
  const end = useAutoScroll(live, steps.length)

  return (
    <div>
      <ol className="flex flex-col gap-3" aria-label="Agent reasoning steps" aria-live={live ? 'polite' : 'off'}>
        {steps.map((step) => (
          <Step key={step.id} step={step} />
        ))}
      </ol>
      {live && (
        <p className="mt-4 flex items-center gap-2 pl-4 text-xs text-gray-500">
          <span className="flex gap-1" aria-hidden="true">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400 motion-reduce:animate-none" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400 [animation-delay:150ms] motion-reduce:animate-none" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400 [animation-delay:300ms] motion-reduce:animate-none" />
          </span>
          Working…
        </p>
      )}
      <div ref={end} />
    </div>
  )
}
