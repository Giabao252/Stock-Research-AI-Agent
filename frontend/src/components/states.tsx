import type { ReactNode } from 'react'
import { AlertIcon, SearchIcon } from './icons'

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-gray-800/80 motion-reduce:animate-none ${className}`} />
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-gray-800 px-6 py-14 text-center">
      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-300">
        <SearchIcon className="h-8 w-8" />
      </div>
      <h2 className="text-lg font-semibold text-gray-100">{title}</h2>
      {children && <p className="mt-2 max-w-sm text-sm text-gray-400">{children}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}

export function ErrorPanel({ title, message, action }: { title: string; message: string; action?: ReactNode }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center rounded-2xl border border-rose-500/30 bg-rose-500/5 px-6 py-14 text-center"
    >
      <AlertIcon className="mb-4 h-9 w-9 text-rose-300" />
      <h2 className="text-lg font-semibold text-gray-100">{title}</h2>
      <p className="mt-2 max-w-md break-words text-sm text-gray-300">{message}</p>
      {action && <div className="mt-6 flex gap-3">{action}</div>}
    </div>
  )
}

export function Banner({ tone, title, children }: { tone: 'warning' | 'info'; title: string; children?: ReactNode }) {
  const style =
    tone === 'warning'
      ? 'border-amber-500/30 bg-amber-500/10 text-amber-100'
      : 'border-indigo-500/30 bg-indigo-500/10 text-indigo-100'
  return (
    <div role="status" className={`flex gap-3 rounded-xl border px-4 py-3 text-sm ${style}`}>
      <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        <p className="font-semibold">{title}</p>
        {children && <p className="mt-0.5 opacity-90">{children}</p>}
      </div>
    </div>
  )
}
