import { useState, type FormEvent } from 'react'
import { Button } from './Button'
import { ArrowIcon, SpinnerIcon } from './icons'

interface Props {
  placeholder: string
  onSubmit: (text: string) => void
  busy?: boolean
  initialValue?: string
}

export function PromptField({ placeholder, onSubmit, busy = false, initialValue = '' }: Props) {
  const [text, setText] = useState(initialValue)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const value = text.trim()
    if (!value || busy) return
    onSubmit(value)
    setText('')
  }

  return (
    <form onSubmit={submit} className="flex gap-2 print:hidden">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="min-w-0 flex-1 rounded-xl border border-gray-700 bg-gray-900 px-4 py-3 text-sm text-gray-100 placeholder:text-gray-500 focus:border-indigo-400 focus:outline-2 focus:outline-indigo-400/40"
      />
      <Button type="submit" variant="primary" disabled={busy || !text.trim()} aria-label="Send question">
        {busy ? <SpinnerIcon /> : <ArrowIcon />}
      </Button>
    </form>
  )
}
