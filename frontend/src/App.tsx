import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { NavBar } from './components/NavBar'
import { ToastProvider } from './components/ToastProvider'
import Compare from './pages/Compare'
import History from './pages/History'
import Home from './pages/Home'
import Report from './pages/Report'
import ReportCompare from './pages/ReportCompare'

function NotFound() {
  return (
    <main className="mx-auto flex max-w-md flex-col items-center gap-3 px-4 py-24 text-center">
      <h1 className="text-xl font-semibold text-gray-100">Page not found</h1>
      <Link to="/" className="text-sm text-indigo-300 hover:underline">
        Back to search
      </Link>
    </main>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        {/* print: the dark UI is inverted to dark-on-white so "Download as PDF" is legible */}
        <div className="min-h-screen bg-gray-950 text-gray-100 print:invert print:hue-rotate-180">
          <NavBar />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/report/:ticker" element={<Report />} />
            <Route path="/history" element={<History />} />
            <Route path="/history/compare/:id1/:id2" element={<ReportCompare />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
      </ToastProvider>
    </BrowserRouter>
  )
}
