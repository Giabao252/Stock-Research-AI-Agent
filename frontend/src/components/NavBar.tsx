import { Link, NavLink } from 'react-router-dom'
import { useActiveRuns } from '../hooks/useRuns'
import { SpinnerIcon } from './icons'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-1 py-1 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-indigo-400 ${
    isActive ? 'font-semibold text-white' : 'text-gray-400 hover:text-gray-200'
  }`

/** Shows while any run is streaming; clicking returns to that run's report. */
function ActiveRunIndicator() {
  const active = useActiveRuns()
  if (active.length === 0) return null
  const latest = active[active.length - 1]
  const label = active.length === 1 ? `${latest.ticker} running` : `${active.length} runs active`

  return (
    <Link
      to={active.length === 1 ? `/report/${latest.ticker}?run=${latest.id}` : '/compare'}
      className="ml-auto inline-flex items-center gap-2 rounded-full border border-indigo-500/40 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-200 hover:bg-indigo-500/20 focus-visible:outline-2 focus-visible:outline-indigo-400"
    >
      <SpinnerIcon className="h-3 w-3" />
      {label}
    </Link>
  )
}

export function NavBar() {
  return (
    <nav className="flex items-center gap-5 border-b border-gray-800 bg-gray-950 px-4 py-3 sm:gap-6 sm:px-6 print:hidden">
      <Link to="/" className="mr-2 font-bold tracking-tight text-gray-100 focus-visible:outline-2 focus-visible:outline-indigo-400">
        StockBuddy
      </Link>
      <NavLink to="/" end className={linkClass}>
        Search
      </NavLink>
      <NavLink to="/history" className={linkClass}>
        History
      </NavLink>
      <NavLink to="/compare" className={linkClass}>
        Compare
      </NavLink>
      <ActiveRunIndicator />
    </nav>
  )
}
