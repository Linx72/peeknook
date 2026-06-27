import { useEffect, useState } from 'react'
import { getDefaultModels, listModels, updateDefaultModels, type Model } from '../api'
import { useI18n } from '../i18n'

export default function DefaultModelsSettings() {
  const { t } = useI18n()
  const d = t.defaultModels
  const [models, setModels] = useState<Model[]>([])
  const [chat, setChat] = useState('')
  const [embedding, setEmbedding] = useState('')
  const [transformation, setTransformation] = useState('')
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([listModels(), getDefaultModels()]).then(([m, defs]) => {
      setModels(m)
      if (defs.default_chat_model) setChat(defs.default_chat_model)
      if (defs.default_embedding_model) setEmbedding(defs.default_embedding_model)
      if (defs.default_transformation_model) setTransformation(defs.default_transformation_model)
    })
  }, [])

  async function onSave() {
    await updateDefaultModels({
      default_chat_model: chat || null,
      default_embedding_model: embedding || null,
      default_transformation_model: transformation || null,
    })
    setMsg(d.saved)
  }

  const language = models.filter((m) => m.type === 'language')
  const embeddingModels = models.filter((m) => m.type === 'embedding')

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-6 space-y-3 text-sm">
      <h3 className="font-semibold">{d.title}</h3>
      <label className="block">
        {d.chat}
        <select className="mt-1 w-full rounded border px-3 py-2" value={chat} onChange={(e) => setChat(e.target.value)}>
          <option value="">—</option>
          {language.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} ({m.provider})
            </option>
          ))}
        </select>
      </label>
      <label className="block">
        {d.embedding}
        <select
          className="mt-1 w-full rounded border px-3 py-2"
          value={embedding}
          onChange={(e) => setEmbedding(e.target.value)}
        >
          <option value="">—</option>
          {embeddingModels.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} ({m.provider})
            </option>
          ))}
        </select>
      </label>
      <label className="block">
        {d.transformation}
        <select
          className="mt-1 w-full rounded border px-3 py-2"
          value={transformation}
          onChange={(e) => setTransformation(e.target.value)}
        >
          <option value="">—</option>
          {language.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} ({m.provider})
            </option>
          ))}
        </select>
      </label>
      <button type="button" onClick={onSave} className="rounded bg-amber-600 px-3 py-2 text-white">
        {d.save}
      </button>
      {msg && <p className="text-stone-600 text-xs">{msg}</p>}
    </section>
  )
}
