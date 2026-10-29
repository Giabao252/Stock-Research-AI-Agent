import type { useTickerSearch } from '../hooks/useTickerSearch'
import { SearchIcon } from './icons'

type Search = ReturnType<typeof useTickerSearch>

interface Props {
  search: Search
  placeholder: string
  label: string
  large?: boolean
  autoFocus?: boolean
  disabled?: boolean
}

/** Combobox with autocomplete over the bundled S&P 500 list. All state lives in useTickerSearch. */
export function TickerSearchBox({ search, placeholder, label, large = false, autoFocus = false, disabled = false }: Props) {
  const optionId = (i: number) => `${search.listId}-option-${i}`

  return (
    <div className="relative w-full">
      <SearchIcon
        className={`pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 ${large ? 'h-5 w-5' : 'h-4 w-4'}`}
      />
      <input
        type="text"
        role="combobox"
        aria-label={label}
        aria-expanded={search.showList}
        aria-controls={search.listId}
        aria-autocomplete="list"
        aria-activedescendant={search.activeIndex >= 0 ? optionId(search.activeIndex) : undefined}
        autoComplete="off"
        autoCapitalize="off"
        spellCheck={false}
        autoFocus={autoFocus}
        disabled={disabled}
        value={search.query}
        placeholder={placeholder}
        onChange={search.onChange}
        onKeyDown={search.onKeyDown}
        onFocus={search.onFocus}
        onBlur={search.onBlur}
        className={`w-full rounded-xl border border-gray-700 bg-gray-900 text-gray-100 placeholder:text-gray-500 focus:border-indigo-400 focus:outline-2 focus:outline-indigo-400/40 disabled:opacity-50 ${
          large ? 'py-4 pl-12 pr-4 text-lg' : 'py-2.5 pl-10 pr-4 text-sm'
        }`}
      />
      {search.showList && (
        <ul
          id={search.listId}
          role="listbox"
          className="absolute z-20 mt-2 max-h-80 w-full overflow-auto rounded-xl border border-gray-700 bg-gray-900 py-1 shadow-2xl"
        >
          {search.results.map((company, i) => (
            <li
              key={company.symbol}
              id={optionId(i)}
              role="option"
              aria-selected={i === search.activeIndex}
              // mousedown (not click) + preventDefault keeps focus in the input so blur doesn't close the list first
              onMouseDown={(event) => {
                event.preventDefault()
                search.choose(company)
              }}
              onMouseEnter={() => search.setActiveIndex(i)}
              className={`flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm ${
                i === search.activeIndex ? 'bg-indigo-500/15' : ''
              }`}
            >
              <span className="w-14 shrink-0 font-semibold tabular-nums text-gray-100">{company.symbol}</span>
              <span className="truncate text-gray-400">{company.name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
