import { useEffect, useState } from 'react'
import {
  cloudLogin,
  cloudRegister,
  getSetupStatus,
  pullSyncFromCloud,
  pushSyncToCloud,
  updatePeeknookSettings,
  type SetupStatus,
} from '../api'
import { useI18n } from '../i18n'
import { fmt } from '../i18n/format'

const CLOUD_KEY = 'peeknook_cloud_url'
const TOKEN_KEY = 'peeknook_cloud_token'
const EMAIL_KEY = 'peeknook_cloud_email'

export default function CloudSync() {
  const { t } = useI18n()
  const c = t.cloud
  const [status, setStatus] = useState<SetupStatus | null>(null)
  const [cloudUrl, setCloudUrl] = useState(localStorage.getItem(CLOUD_KEY) || 'http://127.0.0.1:8090')
  const [email, setEmail] = useState(localStorage.getItem(EMAIL_KEY) || '')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY) || '')
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getSetupStatus().then(setStatus).catch(() => setStatus(null))
  }, [])

  async function persistCloud(tokenValue: string) {
    localStorage.setItem(CLOUD_KEY, cloudUrl)
    localStorage.setItem(TOKEN_KEY, tokenValue)
    await updatePeeknookSettings({ cloud_url: cloudUrl, cloud_token: tokenValue })
  }

  async function auth(mode: 'login' | 'register') {
    setBusy(true)
    setMsg(null)
    try {
      localStorage.setItem(CLOUD_KEY, cloudUrl)
      localStorage.setItem(EMAIL_KEY, email)
      const fn = mode === 'login' ? cloudLogin : cloudRegister
      const res = await fn(email, password, cloudUrl)
      localStorage.setItem(TOKEN_KEY, res.access_token)
      setToken(res.access_token)
      await persistCloud(res.access_token)
      setMsg(mode === 'login' ? c.loggedIn : c.registered)
    } catch (e) {
      setMsg(String(e))
    } finally {
      setBusy(false)
    }
  }

  async function push() {
    if (!token) return setMsg(c.loginFirst)
    setBusy(true)
    try {
      const r = await pushSyncToCloud(token, cloudUrl)
      setMsg(fmt(c.pushed, { events: r.pushed ?? 0, blobs: r.blobs ?? 0 }))
      getSetupStatus().then(setStatus)
    } catch (e) {
      setMsg(String(e))
    } finally {
      setBusy(false)
    }
  }

  async function pull() {
    if (!token) return setMsg(c.loginFirst)
    setBusy(true)
    try {
      const r = await pullSyncFromCloud(token, cloudUrl)
      setMsg(fmt(c.pulled, { applied: r.applied ?? 0, results: (r.results ?? []).length }))
    } catch (e) {
      setMsg(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">{c.title}</h2>
      <p className="text-sm text-stone-600">
        {c.subtitle}{' '}
        <a href={cloudUrl} target="_blank" rel="noreferrer" className="text-amber-700 underline">
          {c.dashboard}
        </a>
      </p>

      {status && <p className="text-sm text-stone-500">{fmt(c.pending, { count: status.sync_pending })}</p>}

      <section className="rounded-xl border border-stone-200 bg-white p-4 space-y-3 max-w-lg">
        <input
          className="w-full rounded border border-stone-300 px-3 py-2 text-sm"
          placeholder={c.cloudUrl}
          value={cloudUrl}
          onChange={(e) => setCloudUrl(e.target.value)}
        />
        <input
          className="w-full rounded border border-stone-300 px-3 py-2 text-sm"
          placeholder={c.email}
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="w-full rounded border border-stone-300 px-3 py-2 text-sm"
          placeholder={c.password}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={busy} onClick={() => auth('login')} className="rounded bg-stone-800 px-3 py-2 text-sm text-white">
            {c.login}
          </button>
          <button type="button" disabled={busy} onClick={() => auth('register')} className="rounded border px-3 py-2 text-sm">
            {c.register}
          </button>
          <button type="button" disabled={busy || !token} onClick={push} className="rounded bg-amber-600 px-3 py-2 text-sm text-white">
            {c.push}
          </button>
          <button type="button" disabled={busy || !token} onClick={pull} className="rounded border px-3 py-2 text-sm">
            {c.pull}
          </button>
        </div>
        {token && <p className="text-xs text-green-700">{c.connected}</p>}
        {msg && <p className="text-sm text-stone-700">{msg}</p>}
      </section>
    </div>
  )
}
