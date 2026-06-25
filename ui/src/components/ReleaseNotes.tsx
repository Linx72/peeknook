import { useEffect, useState } from 'react'
import { useI18n } from '../i18n'
import { fetchLatestReleaseNotes, type ReleaseNotes as Notes } from '../lib/releaseAssets'

export default function ReleaseNotes() {
  const { t } = useI18n()
  const n = t.releaseNotes
  const [notes, setNotes] = useState<Notes | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLatestReleaseNotes()
      .then(setNotes)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <section className="rounded-xl border border-stone-200 bg-white p-6 text-sm text-stone-500">
        {n.loading}
      </section>
    )
  }

  if (!notes) {
    return null
  }

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-6 space-y-3 text-sm">
      <h3 className="font-semibold">{n.title}</h3>
      <p className="text-xs text-stone-400">
        {n.versionLabel}: {notes.tag}
        {notes.publishedAt ? ` · ${new Date(notes.publishedAt).toLocaleDateString()}` : ''}
      </p>
      <pre className="whitespace-pre-wrap font-sans text-stone-700 text-sm leading-relaxed max-h-64 overflow-y-auto rounded-lg bg-stone-50 p-3">
        {notes.body}
      </pre>
      <a className="text-xs text-amber-700 underline" href={notes.url} target="_blank" rel="noreferrer">
        {n.viewOnGitHub}
      </a>
    </section>
  )
}
