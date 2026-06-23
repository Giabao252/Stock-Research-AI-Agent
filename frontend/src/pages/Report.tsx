import { useParams } from 'react-router-dom'

export default function Report() {
  const { ticker } = useParams<{ ticker: string }>()

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-gray-100 mb-2">
        Report: {ticker ?? '—'}
      </h1>
      <p className="text-gray-400 text-sm">
        Live run + report view — coming soon
      </p>
    </main>
  )
}
