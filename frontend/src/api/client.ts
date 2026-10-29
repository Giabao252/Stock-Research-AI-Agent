import { z } from 'zod'
import {
  analyzeResponseSchema,
  answerSchema,
  chunkSchema,
  researchReportSchema,
  type AnalyzeResponse,
  type Answer,
  type Chunk,
  type ResearchReport,
} from './schemas'

const envSchema = z.object({ VITE_API_BASE_URL: z.url().default('http://localhost:8000') })
const env = envSchema.parse({ VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL || undefined })

export const API_BASE_URL = env.VITE_API_BASE_URL.replace(/\/+$/, '')

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

/** FastAPI errors are `{detail: string | [...]}`; fall back to the status line. */
async function errorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (body && typeof body === 'object' && 'detail' in body) {
      const { detail } = body as { detail: unknown }
      if (typeof detail === 'string') return detail
    }
  } catch {
    // not JSON — fall through
  }
  return `${response.status} ${response.statusText}`.trim()
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init)
  } catch (error) {
    if (isAbortError(error)) throw error
    throw new ApiError(0, 'Could not reach the server. Check your connection and try again.')
  }
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response))
  return response
}

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, init)
  const body: unknown = await response.json()
  const parsed = schema.safeParse(body)
  if (!parsed.success) {
    console.error(`Unexpected response shape from ${path}`, parsed.error)
    throw new ApiError(502, 'The server returned an unexpected response.')
  }
  return parsed.data
}

export function analyze(ticker: string, signal?: AbortSignal): Promise<AnalyzeResponse> {
  return request('/analyze', analyzeResponseSchema, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker }),
    signal,
  })
}

/** Best-effort cleanup; a failure here never matters to the user. */
export async function deleteSession(sessionId: string): Promise<void> {
  try {
    await apiFetch(`/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
  } catch {
    // session may already be gone or expired
  }
}

export function ask(params: { question: string; ticker: string; sessionId: string }): Promise<Answer> {
  return request('/ask', answerSchema, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: params.question,
      ticker: params.ticker,
      session_id: params.sessionId,
    }),
  })
}

// Completed reports and chunks are immutable, so cache the in-flight/settled promise.
const reportCache = new Map<string, Promise<ResearchReport>>()
const chunkCache = new Map<string, Promise<Chunk>>()

function cached<T>(cache: Map<string, Promise<T>>, key: string, load: () => Promise<T>): Promise<T> {
  const hit = cache.get(key)
  if (hit) return hit
  const pending = load().catch((error: unknown) => {
    cache.delete(key) // never cache a failure
    throw error
  })
  cache.set(key, pending)
  return pending
}

export function getReport(reportId: string): Promise<ResearchReport> {
  return cached(reportCache, reportId, () =>
    request(`/reports/${encodeURIComponent(reportId)}`, researchReportSchema),
  )
}

export function getChunk(chunkId: string): Promise<Chunk> {
  return cached(chunkCache, chunkId, () => request(`/chunks/${encodeURIComponent(chunkId)}`, chunkSchema))
}
