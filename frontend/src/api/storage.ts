import { z } from 'zod'

// Browser-side persistence. The backend has no "list all reports" endpoint and no stable
// report id on list results, so the reports a user generated are tracked here by id and
// fetched individually via GET /reports/{id}.

const HISTORY_KEY = 'stockbuddy:history'
const RECENT_KEY = 'stockbuddy:recent'
const MAX_RECENT = 5

const historyEntrySchema = z.object({
  reportId: z.string(),
  ticker: z.string(),
})
export type HistoryEntry = z.infer<typeof historyEntrySchema>

function read<T>(key: string, schema: z.ZodType<T>, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key)
    if (!raw) return fallback
    const parsed = schema.safeParse(JSON.parse(raw))
    return parsed.success ? parsed.data : fallback
  } catch {
    return fallback // storage blocked or corrupt JSON
  }
}

function write(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // quota exceeded / private mode — history is a convenience, not critical
  }
}

export function loadHistoryIndex(): HistoryEntry[] {
  return read(HISTORY_KEY, z.array(historyEntrySchema), [])
}

export function addHistoryEntry(entry: HistoryEntry): void {
  const rest = loadHistoryIndex().filter((e) => e.reportId !== entry.reportId)
  write(HISTORY_KEY, [entry, ...rest])
}

export function removeHistoryEntry(reportId: string): void {
  write(
    HISTORY_KEY,
    loadHistoryIndex().filter((e) => e.reportId !== reportId),
  )
}

export function loadRecentTickers(): string[] {
  return read(RECENT_KEY, z.array(z.string()), [])
}

export function pushRecentTicker(ticker: string): void {
  const rest = loadRecentTickers().filter((t) => t !== ticker)
  write(RECENT_KEY, [ticker, ...rest].slice(0, MAX_RECENT))
}
