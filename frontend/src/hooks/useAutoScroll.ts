import { useEffect, useRef } from 'react'

const STICK_DISTANCE_PX = 160

/**
 * Keeps the newest streamed step in view — but only while the reader is already near the
 * bottom, so scrolling up to re-read earlier steps isn't fought by incoming ones.
 */
export function useAutoScroll(enabled: boolean, changeKey: number) {
  const end = useRef<HTMLDivElement>(null)
  const stuck = useRef(true)

  useEffect(() => {
    if (!enabled) return
    const onScroll = () => {
      const distance = document.documentElement.scrollHeight - window.innerHeight - window.scrollY
      stuck.current = distance < STICK_DISTANCE_PX
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [enabled])

  useEffect(() => {
    if (enabled && stuck.current) end.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [enabled, changeKey])

  return end
}
