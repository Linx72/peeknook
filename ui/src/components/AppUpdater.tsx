import { useState } from 'react'
import { useI18n } from '../i18n'
import { fmt } from '../i18n/format'
import { isTauriApp } from '../lib/isTauri'

type Status = 'idle' | 'checking' | 'installing' | 'done' | 'error'

export default function AppUpdater() {
  const { t } = useI18n()
  const u = t.updates
  const [status, setStatus] = useState<Status>('idle')
  const [message, setMessage] = useState<string | null>(null)

  if (!isTauriApp()) {
    return (
      <section className="rounded-xl border border-stone-200 bg-white p-6 space-y-2 text-sm">
        <h3 className="font-semibold">{u.title}</h3>
        <p className="text-stone-500">{u.desktopOnly}</p>
      </section>
    )
  }

  async function onCheck() {
    setStatus('checking')
    setMessage(null)
    try {
      const { check } = await import('@tauri-apps/plugin-updater')
      const { relaunch } = await import('@tauri-apps/plugin-process')
      const update = await check()
      if (!update) {
        setStatus('done')
        setMessage(u.upToDate)
        return
      }
      setMessage(fmt(u.available, { version: update.version }))
      if (update.body) {
        setMessage((m) => `${m}\n${update.body}`)
      }
      setStatus('installing')
      await update.downloadAndInstall()
      setStatus('done')
      setMessage(fmt(u.installed, { version: update.version }))
      await relaunch()
    } catch (err) {
      setStatus('error')
      setMessage(String(err))
    }
  }

  const busy = status === 'checking' || status === 'installing'

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-6 space-y-3 text-sm">
      <h3 className="font-semibold">{u.title}</h3>
      <p className="text-stone-500 text-xs">{u.hint}</p>
      <button
        type="button"
        disabled={busy}
        onClick={onCheck}
        className="rounded bg-stone-800 px-3 py-2 text-white disabled:opacity-50"
      >
        {status === 'checking' ? u.checking : status === 'installing' ? u.installing : u.check}
      </button>
      {message && (
        <p className={`text-xs ${status === 'error' ? 'text-red-700' : 'text-stone-600'}`}>{message}</p>
      )}
    </section>
  )
}
