import { createContext, useContext } from 'react'
import type { ToastOptions } from './useToastState'

export interface ToastApi {
  show: (options: ToastOptions) => number
  dismiss: (id: number) => void
}

export const ToastContext = createContext<ToastApi | null>(null)

export function useToast(): ToastApi {
  const api = useContext(ToastContext)
  if (!api) throw new Error('useToast must be used inside <ToastProvider>')
  return api
}
