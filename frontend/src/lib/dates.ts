const HAS_TIMEZONE = /(Z|[+-]\d{2}:?\d{2})$/i

/** The backend serialises some datetimes without a timezone; those are UTC. */
export function parseServerDate(value: string): Date {
  return new Date(HAS_TIMEZONE.test(value) ? value : `${value}Z`)
}

const dateTime = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' })
const dateOnly = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium' })

export function formatDateTime(date: Date): string {
  return Number.isNaN(date.getTime()) ? 'Unknown date' : dateTime.format(date)
}

export function formatDate(date: Date): string {
  return Number.isNaN(date.getTime()) ? 'Unknown date' : dateOnly.format(date)
}
