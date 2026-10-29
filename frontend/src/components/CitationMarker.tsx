interface Props {
  number: number
  onClick: () => void
}

export function CitationMarker({ number, onClick }: Props) {
  return (
    <sup className="ml-0.5">
      <button
        type="button"
        onClick={onClick}
        aria-label={`View source ${number}`}
        className="inline-flex min-h-5 min-w-5 items-center justify-center rounded px-1 text-[0.7rem] font-semibold leading-none text-indigo-300 hover:bg-indigo-500/20 hover:text-indigo-200 focus-visible:outline-2 focus-visible:outline-indigo-400"
      >
        {number}
      </button>
    </sup>
  )
}
