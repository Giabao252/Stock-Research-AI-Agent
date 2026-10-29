export type ToolKind = 'filings' | 'market' | 'web' | 'edgar' | 'calc' | 'system'

export interface ToolSummary {
  kind: ToolKind
  /** Human-readable one-liner — never raw JSON. */
  text: string
}

const MAX_DETAIL = 90

/** Tools are namespaced `mcp__stock-research__rag_retrieval_tool`; keep the last segment. */
export function shortToolName(tool: string): string {
  return tool.split('__').pop() ?? tool
}

function str(args: Record<string, unknown>, key: string): string | null {
  const value = args[key]
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

function clip(value: string): string {
  return value.length > MAX_DETAIL ? `${value.slice(0, MAX_DETAIL - 1)}…` : value
}

export function summarizeToolCall(tool: string, args: Record<string, unknown>): ToolSummary {
  const name = shortToolName(tool)
  const query = str(args, 'query')
  const ticker = str(args, 'ticker')

  switch (name) {
    case 'rag_retrieval_tool':
      return { kind: 'filings', text: query ? `Searched filings for “${clip(query)}”` : 'Searched filings' }
    case 'stock_data_tool':
      return { kind: 'market', text: ticker ? `Fetched market data for ${ticker}` : 'Fetched market data' }
    case 'web_search_tool':
      return { kind: 'web', text: query ? `Searched the web for “${clip(query)}”` : 'Searched the web' }
    case 'edgar_fetch_tool':
      return { kind: 'edgar', text: ticker ? `Pulled SEC filings for ${ticker}` : 'Pulled SEC filings' }
    case 'code_execution_tool':
      return { kind: 'calc', text: 'Ran calculations' }
    case 'ToolSearch':
      return { kind: 'system', text: 'Loaded research tools' }
    case 'StructuredOutput':
      return { kind: 'system', text: 'Wrote the final report' }
    default:
      return { kind: 'system', text: `Called ${name.replace(/_/g, ' ')}` }
  }
}

/** Observe summaries for failed tools start "<tool> failed: …" — worth flagging in the chain. */
export function isFailureSummary(summary: string): boolean {
  return /\bfailed:/i.test(summary)
}
