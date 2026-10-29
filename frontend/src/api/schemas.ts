import { z } from 'zod'
import { parseServerDate } from '../lib/dates'

// Mirrors backend/app/models/*.py field-for-field.

export const claimSchema = z.object({
  text: z.string(),
  chunk_id: z.string().nullable(), // null for claims sourced from web search
  source_url: z.string(),
  doc_name: z.string(),
})

export const toolCallSchema = z.object({
  tool: z.string(),
  args: z.record(z.string(), z.unknown()),
  result_summary: z.string(),
})

export const verdictSchema = z.enum(['bullish', 'bearish', 'neutral'])

export const researchReportSchema = z.object({
  ticker: z.string(),
  bull_case: z.array(claimSchema),
  bear_case: z.array(claimSchema),
  verdict: verdictSchema,
  confidence: z.number(), // 0..1
  tool_trace: z.array(toolCallSchema),
  metrics: z.record(z.string(), z.unknown()),
  partial: z.boolean(),
  partial_reason: z.string().nullish().transform((v) => v ?? null),
  generated_at: z.string().transform(parseServerDate),
})

export const chunkSchema = z.object({
  chunk_id: z.string(),
  text: z.string(),
  ticker: z.string(),
  section: z.string(),
  year: z.number(),
  source_url: z.string(),
  score: z.number(),
})

export const answerSchema = z.object({
  text: z.string(),
  sources: z.array(claimSchema),
})

export const analyzeResponseSchema = z.object({
  session_id: z.string(),
  ticker: z.string(),
})

export const streamEventSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('thought'), content: z.string() }),
  z.object({ type: z.literal('tool_call'), tool: z.string(), args: z.record(z.string(), z.unknown()) }),
  z.object({ type: z.literal('observe'), summary: z.string() }),
  z.object({ type: z.literal('done'), report_id: z.string() }),
  z.object({ type: z.literal('error'), message: z.string() }),
])

export type Claim = z.infer<typeof claimSchema>
export type ToolCall = z.infer<typeof toolCallSchema>
export type ResearchReport = z.infer<typeof researchReportSchema>
export type Chunk = z.infer<typeof chunkSchema>
export type Answer = z.infer<typeof answerSchema>
export type AnalyzeResponse = z.infer<typeof analyzeResponseSchema>
export type StreamEvent = z.infer<typeof streamEventSchema>
