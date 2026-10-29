import { useId, useMemo, useState, type ChangeEvent, type KeyboardEvent } from 'react'
import { searchCompanies, type Company } from '../lib/companies'

interface Options {
  /** A company was picked from the list. */
  onSelectCompany: (company: Company) => void
  /** Enter was pressed with nothing highlighted — receives the raw text. */
  onSubmitText: (text: string) => void
}

/** Autocomplete state + keyboard handling for the ticker/company search box. */
export function useTickerSearch({ onSelectCompany, onSubmitText }: Options) {
  const listId = useId()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)

  const results = useMemo(() => searchCompanies(query), [query])
  const showList = open && results.length > 0

  const reset = () => {
    setQuery('')
    setOpen(false)
    setActiveIndex(-1)
  }

  const choose = (company: Company) => {
    reset()
    onSelectCompany(company)
  }

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    setQuery(event.target.value)
    setOpen(true)
    setActiveIndex(-1)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        setOpen(true)
        setActiveIndex((i) => (results.length ? (i + 1) % results.length : -1))
        break
      case 'ArrowUp':
        event.preventDefault()
        setActiveIndex((i) => (results.length ? (i <= 0 ? results.length - 1 : i - 1) : -1))
        break
      case 'Escape':
        setOpen(false)
        setActiveIndex(-1)
        break
      case 'Enter': {
        event.preventDefault()
        const picked = showList ? results[activeIndex] : undefined
        if (picked) {
          choose(picked)
        } else if (query.trim()) {
          const text = query
          reset()
          onSubmitText(text)
        }
        break
      }
    }
  }

  return {
    listId,
    query,
    results,
    showList,
    activeIndex,
    setActiveIndex,
    choose,
    onChange,
    onKeyDown,
    onFocus: () => setOpen(true),
    onBlur: () => setOpen(false),
  }
}
