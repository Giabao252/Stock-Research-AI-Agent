/**
 * Claim source URLs are written by the model, so they are untrusted: only plain
 * http(s) links may become an href (a `javascript:` URL would be an XSS vector).
 */
export function safeHttpUrl(value: string): string | null {
  try {
    const url = new URL(value)
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.toString() : null
  } catch {
    return null
  }
}

export function hostnameOf(value: string): string {
  try {
    return new URL(value).hostname.replace(/^www\./, '')
  } catch {
    return value
  }
}
