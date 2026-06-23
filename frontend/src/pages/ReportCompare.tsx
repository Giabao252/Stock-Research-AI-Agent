import { useParams } from 'react-router-dom'

export default function ReportCompare() {
  const { id1, id2 } = useParams<{ id1: string; id2: string }>()

  return (
    <main className="max-w-6xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-gray-100 mb-2">
        Comparing reports
      </h1>
      <p className="text-gray-400 text-sm">
        {id1 ?? '—'} vs {id2 ?? '—'} — side-by-side view coming soon
      </p>
    </main>
  )
}
