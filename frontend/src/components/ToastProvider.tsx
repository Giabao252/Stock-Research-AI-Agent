import type { ReactNode } from 'react'
import { ToastContext } from '../hooks/toastContext'
import { useToastState } from '../hooks/useToastState'

export function ToastProvider({ children }: { children: ReactNode }) {
  const { toasts, show, dismiss } = useToastState()

  return (
    <ToastContext.Provider value={{ show, dismiss }}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4 print:hidden"
        role="status"
        aria-live="polite"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="pointer-events-auto flex items-center gap-4 rounded-lg border border-gray-700 bg-gray-900 px-4 py-3 text-sm text-gray-100 shadow-xl transition duration-200 starting:translate-y-2 starting:opacity-0"
          >
            <span>{toast.message}</span>
            {toast.actionLabel && (
              <button
                type="button"
                onClick={() => {
                  toast.onAction?.()
                  dismiss(toast.id)
                }}
                className="font-semibold text-indigo-300 hover:text-indigo-200 focus-visible:outline-2 focus-visible:outline-indigo-400"
              >
                {toast.actionLabel}
              </button>
            )}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
