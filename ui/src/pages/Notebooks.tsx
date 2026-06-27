import { type FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { createNotebook, listNotebooks, type Notebook } from '../api'
import { useI18n } from '../i18n'

export default function Notebooks() {
  const { t } = useI18n()
  const n = t.notebooks
  const [items, setItems] = useState<Notebook[]>([])
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(true)

  const reload = () => {
    setLoading(true)
    listNotebooks()
      .then(setItems)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    reload()
  }, [])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    await createNotebook(name.trim(), n.createdDesc)
    setName('')
    reload()
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">{n.title}</h2>

      <form onSubmit={onCreate} className="flex gap-2">
        <input
          className="flex-1 rounded-lg border border-stone-300 px-3 py-2"
          placeholder={n.placeholder}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button className="rounded-lg bg-amber-600 px-4 py-2 text-white hover:bg-amber-700" type="submit">
          {n.create}
        </button>
      </form>

      {loading ? (
        <p className="text-stone-500">{n.loading}</p>
      ) : items.length === 0 ? (
        <p className="text-stone-500">{n.empty}</p>
      ) : (
        <ul className="divide-y divide-stone-200 rounded-xl border border-stone-200 bg-white">
          {items.map((nb) => (
            <li key={nb.id} className="flex items-center justify-between px-4 py-3">
              <Link to={`/notebooks/${nb.id}`} className="flex-1 hover:text-amber-700">
                <div className="font-medium">{nb.name}</div>
                {nb.description && <div className="text-sm text-stone-500">{nb.description}</div>}
              </Link>
              <div className="text-xs text-stone-400">
                {nb.source_count ?? 0} {n.sources}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
