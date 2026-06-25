import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  buildChatContext,
  createChatSession,
  createNote,
  deleteNote,
  getNotebook,
  getSourceStatus,
  listNotes,
  listSources,
  streamChatMessage,
  uploadPdf,
  type ChatMessage,
  type Note,
  type Notebook,
  type Source,
} from '../api'
import { useI18n } from '../i18n'

export default function NotebookDetail() {
  const { t } = useI18n()
  const n = t.notebookDetail
  const { id = '' } = useParams()
  const [notebook, setNotebook] = useState<Notebook | null>(null)
  const [sources, setSources] = useState<Source[]>([])
  const [notes, setNotes] = useState<Note[]>([])
  const [noteTitle, setNoteTitle] = useState('')
  const [noteContent, setNoteContent] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    if (!id) return
    const [nb, src, nts] = await Promise.all([getNotebook(id), listSources(id), listNotes(id)])
    setNotebook(nb)
    setSources(src)
    setNotes(nts)
  }, [id])

  useEffect(() => {
    reload().catch((e) => setError(String(e)))
  }, [reload])

  useEffect(() => {
    const pending = sources.filter((s) => s.embedded === false)
    if (pending.length === 0) return
    const timer = setInterval(async () => {
      let changed = false
      for (const s of pending) {
        try {
          const st = await getSourceStatus(s.id)
          if (st.status === 'completed' || st.status === 'failed') changed = true
        } catch {
          /* ignore poll errors */
        }
      }
      if (changed) reload().catch(() => undefined)
    }, 3000)
    return () => clearInterval(timer)
  }, [sources, reload])

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !id) return
    setUploading(true)
    setError(null)
    try {
      await uploadPdf(id, file)
      await reload()
    } catch (err) {
      setError(String(err))
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  async function onAddNote(e: FormEvent) {
    e.preventDefault()
    if (!id || !noteContent.trim()) return
    setError(null)
    try {
      await createNote(id, noteTitle.trim() || 'Note', noteContent.trim())
      setNoteTitle('')
      setNoteContent('')
      await reload()
    } catch (err) {
      setError(String(err))
    }
  }

  async function onDeleteNote(noteId: string) {
    setError(null)
    try {
      await deleteNote(noteId)
      await reload()
    } catch (err) {
      setError(String(err))
    }
  }

  async function onSend(e: FormEvent) {
    e.preventDefault()
    if (!input.trim() || !id || busy) return
    setBusy(true)
    setError(null)
    const text = input.trim()
    setInput('')
    setMessages((m) => [...m, { id: `u-${Date.now()}`, type: 'human', content: text }])

    try {
      let sid = sessionId
      if (!sid) {
        const session = await createChatSession(id, text.slice(0, 40))
        sid = session.id
        setSessionId(sid)
      }
      const sourceIds = sources.map((s) => s.id)
      const { context } = await buildChatContext(id, sourceIds)
      const aiId = `ai-${Date.now()}`
      setMessages((m) => [...m, { id: aiId, type: 'ai', content: '' }])
      await streamChatMessage(sid!, text, context as Record<string, unknown>, (ev) => {
        if (ev.type === 'ai_chunk' && ev.content) {
          setMessages((m) =>
            m.map((msg) => (msg.id === aiId ? { ...msg, content: msg.content + ev.content } : msg)),
          )
        }
        if (ev.type === 'complete' && ev.content) {
          setMessages((m) =>
            m.map((msg) => (msg.id === aiId ? { ...msg, content: ev.content! } : msg)),
          )
        }
        if (ev.type === 'error') setError(ev.message || n.chatError)
      })
    } catch (err) {
      setError(String(err))
    } finally {
      setBusy(false)
    }
  }

  if (!notebook) {
    return <p className="text-stone-500">{n.loading}</p>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-stone-500">
        <Link to="/notebooks" className="hover:text-amber-700">{t.nav.notebooks}</Link>
        <span>/</span>
        <span>{notebook.name}</span>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>
      )}

      <section className="rounded-xl border border-stone-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">{n.sources}</h2>
          <label className="cursor-pointer rounded-lg bg-amber-600 px-3 py-2 text-sm text-white hover:bg-amber-700">
            {uploading ? n.uploading : n.uploadPdf}
            <input type="file" accept=".pdf,.doc,.docx,.txt,.md" className="hidden" onChange={onUpload} disabled={uploading} />
          </label>
        </div>
        <ul className="mt-3 divide-y divide-stone-100">
          {sources.length === 0 ? (
            <li className="py-3 text-sm text-stone-500">{n.noSources}</li>
          ) : (
            sources.map((s) => (
              <li key={s.id} className="py-2 text-sm">
                <span className="font-medium">{s.title || s.id}</span>
                {s.embedded === false && <span className="ml-2 text-amber-600">{n.processing}</span>}
              </li>
            ))
          )}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-4">
        <h2 className="text-lg font-semibold">{n.notes}</h2>
        <ul className="mt-3 divide-y divide-stone-100">
          {notes.length === 0 ? (
            <li className="py-3 text-sm text-stone-500">{n.noNotes}</li>
          ) : (
            notes.map((note) => (
              <li key={note.id} className="py-2 text-sm">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="font-medium">{note.title || n.untitled}</span>
                    {note.content && (
                      <p className="mt-1 text-stone-600 line-clamp-2 whitespace-pre-wrap">{note.content}</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => onDeleteNote(note.id)}
                    className="text-xs text-red-600 hover:underline"
                  >
                    {t.common.delete}
                  </button>
                </div>
              </li>
            ))
          )}
        </ul>
        <form onSubmit={onAddNote} className="mt-4 space-y-2">
          <input
            className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
            placeholder={n.noteTitle}
            value={noteTitle}
            onChange={(e) => setNoteTitle(e.target.value)}
          />
          <textarea
            className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
            rows={3}
            placeholder={n.noteContent}
            value={noteContent}
            onChange={(e) => setNoteContent(e.target.value)}
          />
          <button type="submit" className="rounded-lg bg-stone-800 px-3 py-2 text-sm text-white">
            {n.addNote}
          </button>
        </form>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-4">
        <h2 className="text-lg font-semibold">{n.chat}</h2>
        <div className="mt-3 max-h-96 space-y-3 overflow-y-auto rounded-lg bg-stone-50 p-3">
          {messages.length === 0 ? (
            <p className="text-sm text-stone-500">{n.chatEmpty}</p>
          ) : (
            messages.map((m) => (
              <div key={m.id} className={m.type === 'human' ? 'text-right' : 'text-left'}>
                <div
                  className={`inline-block max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                    m.type === 'human' ? 'bg-amber-600 text-white' : 'bg-white border border-stone-200'
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))
          )}
        </div>
        <form onSubmit={onSend} className="mt-3 flex gap-2">
          <input
            className="flex-1 rounded-lg border border-stone-300 px-3 py-2 text-sm"
            placeholder={n.chatPlaceholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="rounded-lg bg-stone-900 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {busy ? '…' : t.common.send}
          </button>
        </form>
      </section>
    </div>
  )
}
