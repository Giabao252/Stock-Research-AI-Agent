import { useElapsedSeconds } from '../hooks/useElapsed'
import { Button } from './Button'
import { StopIcon } from './icons'

interface Props {
  startedAt: number | null
  finalizing: boolean
  onCancel: () => void
}

export function RunProgress({ startedAt, finalizing, onCancel }: Props) {
  const seconds = useElapsedSeconds(startedAt, true)

  return (
    <div className="flex flex-col gap-3 print:hidden" role="status">
      <div className="h-1 w-full overflow-hidden rounded-full bg-gray-800">
        <div className="h-full w-full animate-pulse rounded-full bg-indigo-400 motion-reduce:animate-none" />
      </div>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-gray-400">
          {finalizing ? 'Saving the report…' : 'Researching'} <span className="tabular-nums text-gray-500">· {seconds}s</span>
        </p>
        {!finalizing && (
          <Button variant="secondary" size="sm" onClick={onCancel}>
            <StopIcon className="h-3.5 w-3.5" />
            Cancel
          </Button>
        )}
      </div>
    </div>
  )
}
