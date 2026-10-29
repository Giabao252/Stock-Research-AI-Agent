import { apiFetch } from './client'
import { streamEventSchema, type StreamEvent } from './schemas'

/**
 * Reads GET /sessions/{id}/stream as SSE until the server closes it.
 *
 * Deliberately not `EventSource`: the agent run starts when this connection opens, so
 * EventSource's automatic reconnect would silently start (and bill) a second run after any
 * network blip; and closing the connection on `done` would cancel the server-side step
 * that persists the report. Reading to the natural end avoids both.
 */
export async function streamSession(
  sessionId: string,
  signal: AbortSignal,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const response = await apiFetch(`/sessions/${encodeURIComponent(sessionId)}/stream`, {
    headers: { Accept: 'text/event-stream' },
    signal,
  })
  if (!response.body) throw new Error('The server sent an empty stream.')

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (value) buffer += value
    if (done) break

    let boundary = findFrameBoundary(buffer)
    while (boundary) {
      dispatchFrame(buffer.slice(0, boundary.index), onEvent)
      buffer = buffer.slice(boundary.index + boundary.length)
      boundary = findFrameBoundary(buffer)
    }
  }
  if (buffer.trim()) dispatchFrame(buffer, onEvent)
}

function findFrameBoundary(buffer: string): { index: number; length: number } | null {
  const match = /\r?\n\r?\n/.exec(buffer)
  return match ? { index: match.index, length: match[0].length } : null
}

/** One SSE frame → at most one validated StreamEvent. Comments and unknown shapes are skipped. */
export function parseFrame(frame: string): StreamEvent | null {
  const data = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).replace(/^ /, ''))
    .join('\n')
  if (!data) return null

  let json: unknown
  try {
    json = JSON.parse(data)
  } catch {
    console.warn('Dropped a malformed SSE frame', data)
    return null
  }
  const parsed = streamEventSchema.safeParse(json)
  if (!parsed.success) {
    console.warn('Dropped an unrecognised stream event', json)
    return null
  }
  return parsed.data
}

function dispatchFrame(frame: string, onEvent: (event: StreamEvent) => void): void {
  const event = parseFrame(frame)
  if (event) onEvent(event)
}
