import { type FormEvent, useEffect, useState } from 'react'
import {
  createTransformation,
  deleteTransformation,
  executeTransformation,
  getDefaultModels,
  listModels,
  listTransformations,
  type Model,
  type Transformation,
} from '../api'
import { useI18n } from '../i18n'

export default function Transformations() {
  const { t } = useI18n()
  const tr = t.transformations
  const [items, setItems] = useState<Transformation[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [modelId, setModelId] = useState('')
  const [input, setInput] = useState('')
  const [output, setOutput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [newTitle, setNewTitle] = useState('')
  const [newPrompt, setNewPrompt] = useState('')

  async function reloadItems() {
    const list = await listTransformations()
    setItems(list)
    if (list.length && !selectedId) setSelectedId(list[0].id)
  }

  useEffect(() => {
    Promise.all([listTransformations(), listModels('language'), getDefaultModels()])
      .then(async ([list, m, defaults]) => {
        setItems(list)
        let pool = m.length ? m : await listModels()
        const language = pool.filter((x) => x.type === 'language')
        pool = language.length ? language : pool
        setModels(pool)
        if (list.length) setSelectedId(list[0].id)
        const def = defaults.default_transformation_model || defaults.default_chat_model
        if (def) setModelId(def)
        else if (pool.length) setModelId(pool[0].id)
      })
      .catch((e) => setError(String(e)))
  }, [])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    if (!newName.trim() || !newPrompt.trim()) return
    try {
      const slug = newName.trim().toLowerCase().replace(/\s+/g, '_')
      await createTransformation({
        name: slug,
        title: newTitle.trim() || newName.trim(),
        description: newTitle.trim() || newName.trim(),
        prompt: newPrompt.trim(),
      })
      setNewName('')
      setNewTitle('')
      setNewPrompt('')
      await reloadItems()
    } catch (err) {
      setError(String(err))
    }
  }

  async function onDelete(id: string) {
    if (!confirm(tr.confirmDelete)) return
    await deleteTransformation(id)
    if (selectedId === id) setSelectedId('')
    await reloadItems()
  }

  async function onRun(e: FormEvent) {
    e.preventDefault()
    if (!selectedId || !modelId || !input.trim()) return
    setBusy(true)
    setError(null)
    setOutput('')
    try {
      const r = await executeTransformation(selectedId, input.trim(), modelId)
      setOutput(r.output)
    } catch (err) {
      setError(String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">{tr.title}</h2>
      <p className="text-sm text-stone-600">{tr.subtitle}</p>

      {error && <p className="text-sm text-red-700">{error}</p>}

      <form onSubmit={onRun} className="space-y-4 rounded-xl border bg-white p-4">
        <label className="block text-sm">
          {tr.transformation}
          <select
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
          >
            {items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title || item.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          {tr.model}
          <select
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.provider})
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          {tr.input}
          <textarea
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2 font-mono text-sm"
            rows={6}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={tr.inputPlaceholder}
          />
        </label>

        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-lg bg-amber-600 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {busy ? tr.running : tr.run}
        </button>
      </form>

      {output && (
        <section className="rounded-xl border bg-white p-4">
          <h3 className="font-semibold text-sm mb-2">{tr.output}</h3>
          <pre className="whitespace-pre-wrap text-sm text-stone-800">{output}</pre>
        </section>
      )}

      <section className="rounded-xl border bg-white p-4 space-y-3">
        <h3 className="font-semibold text-sm">{tr.manage}</h3>
        <ul className="divide-y text-sm">
          {items.map((item) => (
            <li key={item.id} className="py-2 flex justify-between gap-2">
              <span>{item.title || item.name}</span>
              <button type="button" onClick={() => onDelete(item.id)} className="text-red-600 text-xs">
                {t.common.delete}
              </button>
            </li>
          ))}
        </ul>
        <form onSubmit={onCreate} className="space-y-2 pt-2 border-t">
          <input
            className="w-full rounded border px-3 py-2 text-sm"
            placeholder={tr.nameSlug}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <input
            className="w-full rounded border px-3 py-2 text-sm"
            placeholder={tr.titleField}
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
          />
          <textarea
            className="w-full rounded border px-3 py-2 text-sm"
            rows={3}
            placeholder={tr.prompt}
            value={newPrompt}
            onChange={(e) => setNewPrompt(e.target.value)}
          />
          <button type="submit" className="rounded bg-stone-800 px-3 py-2 text-sm text-white">
            {tr.create}
          </button>
        </form>
      </section>

      {items.length === 0 && !error && <p className="text-sm text-stone-500">{tr.empty}</p>}
    </div>
  )
}
