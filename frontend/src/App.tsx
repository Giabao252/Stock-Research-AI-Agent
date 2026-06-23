import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Home from './pages/Home'
import Report from './pages/Report'
import History from './pages/History'
import ReportCompare from './pages/ReportCompare'
import Compare from './pages/Compare'

function NavBar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    isActive
      ? 'text-white font-semibold'
      : 'text-gray-400 hover:text-gray-200 transition-colors'

  return (
    <nav className="flex items-center gap-6 px-6 py-4 border-b border-gray-800 bg-gray-950">
      <span className="text-gray-100 font-bold tracking-tight mr-4">StockBuddy</span>
      <NavLink to="/" end className={linkClass}>Search</NavLink>
      <NavLink to="/history" className={linkClass}>History</NavLink>
      <NavLink to="/compare" className={linkClass}>Compare</NavLink>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-gray-100">
        <NavBar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/report/:ticker" element={<Report />} />
          <Route path="/history" element={<History />} />
          <Route path="/history/compare/:id1/:id2" element={<ReportCompare />} />
          <Route path="/compare" element={<Compare />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
