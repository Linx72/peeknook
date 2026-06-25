import { type FormEvent, useState } from 'react'
import { searchKnowledge, type SearchHit } from '../api'
import { useI18n } from '../i18n'

export default function Search() {
  const { t } = useI18n()
  const s = t.search
  const [q, setQ] = useState('')
  const [mode, setMode] = useState<'text' | 'vector'>('text')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSearch(e: FormEvent) {
    e.preventDefault()
    if (!q.trim()) return
    setBusy(true)
    setError(null)
    try {
      const data = await searchKnowledge(q.trim(), 20, mode)
      setHits(data.results || [])
    } catch (err) {
      setError(String(err))
      setHits([])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">{s.title}</h2>
      <form onSubmit={onSearch} className="space-y-3">
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-lg border border-stone-300 px-3 py-2"
            placeholder={s.placeholder}
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <button type="submit" disabled={busy} className="rounded-lg bg-amber-600 px-4 py-2 text-white">
            {busy ? '…' : s.search}
          </button>
        </div>
        <div className="flex gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input type="radio" name="mode" checked={mode === 'text'} onChange={() => setMode('text')} />
            {s.textMode}
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" name="mode" checked={mode === 'vector'} onChange={() => setMode('vector')} />
            {s.vectorMode}
          </label>
        </div>
      </form>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <ul className="divide-y rounded-xl border bg-white">
        {hits.length === 0 ? (
          <li className="p-4 text-sm text-stone-500">{q ? t.common.noResults : s.enterQuery}</li>
        ) : (
          hits.map((h, i) => (
            <li key={i} className="p-4 text-sm">
              <div className="font-medium">{h.title || h.id || s.result}</div>
              {h.content && <p className="mt-1 text-stone-600 line-clamp-3">{String(h.content).slice(0, 300)}</p>}
            </li>
          ))
        )}
      </ul>
    </div>
  )
}
