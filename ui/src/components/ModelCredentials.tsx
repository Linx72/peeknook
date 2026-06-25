import { useCallback, useEffect, useState } from 'react'
import {
  createCredential,
  deleteCredential,
  discoverCredentialModels,
  getCredentialsStatus,
  listCredentials,
  registerCredentialModels,
  syncAllProviderModels,
  syncProviderModels,
  testCredential,
  type Credential,
  type CredentialsStatus,
  type DiscoveredModel,
} from '../api'
import { useI18n } from '../i18n'
import { fmt } from '../i18n/format'

const PROVIDERS = ['ollama', 'openai', 'anthropic', 'google', 'groq', 'openai_compatible']

export default function ModelCredentials() {
  const { t } = useI18n()
  const c = t.credentials
  const [status, setStatus] = useState<CredentialsStatus | null>(null)
  const [items, setItems] = useState<Credential[]>([])
  const [discovered, setDiscovered] = useState<Record<string, DiscoveredModel[]>>({})
  const [name, setName] = useState('')
  const [provider, setProvider] = useState('ollama')
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:11434')
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  const reload = useCallback(async () => {
    const [st, creds] = await Promise.all([getCredentialsStatus(), listCredentials()])
    setStatus(st)
    setItems(creds)
  }, [])

  useEffect(() => {
    reload().catch((e) => setError(String(e)))
  }, [reload])

  async function onAdd(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setMsg(null)
    try {
      await createCredential({
        name: name.trim() || `${provider} default`,
        provider,
        modalities: ['language', 'embedding'],
        api_key: apiKey || undefined,
        base_url: provider === 'ollama' ? baseUrl : undefined,
      })
      setName('')
      setApiKey('')
      setMsg(c.saved)
      await reload()
    } catch (err) {
      setError(String(err))
    }
  }

  async function onTest(id: string) {
    setMsg(null)
    try {
      const r = await testCredential(id)
      setMsg(r.message || r.status || 'OK')
    } catch (err) {
      setError(String(err))
    }
  }

  async function onDelete(id: string) {
    if (!confirm(c.confirmDelete)) return
    await deleteCredential(id)
    setDiscovered((d) => {
      const next = { ...d }
      delete next[id]
      return next
    })
    await reload()
  }

  async function onDiscover(id: string) {
    setBusyId(id)
    setError(null)
    try {
      const r = await discoverCredentialModels(id)
      setDiscovered((d) => ({ ...d, [id]: r.discovered }))
      setMsg(fmt(c.discovered, { count: r.discovered.length }))
    } catch (err) {
      setError(String(err))
    } finally {
      setBusyId(null)
    }
  }

  async function onRegisterAll(cred: Credential) {
    setBusyId(cred.id)
    setError(null)
    try {
      let list = discovered[cred.id]
      if (!list?.length) {
        const r = await discoverCredentialModels(cred.id)
        list = r.discovered
        setDiscovered((d) => ({ ...d, [cred.id]: list }))
      }
      if (!list.length) {
        setMsg(fmt(c.discovered, { count: 0 }))
        return
      }
      const r = await registerCredentialModels(
        cred.id,
        list.map((m) => ({
          name: m.name,
          provider: m.provider || cred.provider,
          model_type: m.model_type || 'language',
        })),
      )
      setMsg(fmt(c.registerSuccess, { created: r.created, existing: r.existing }))
      await reload()
    } catch (err) {
      setError(String(err))
    } finally {
      setBusyId(null)
    }
  }

  async function onSyncProvider(providerName: string) {
    setBusyId(`sync-${providerName}`)
    setError(null)
    try {
      const r = await syncProviderModels(providerName)
      setMsg(fmt(c.syncSuccess, { provider: r.provider, new: r.new, existing: r.existing }))
      await reload()
    } catch (err) {
      setError(String(err))
    } finally {
      setBusyId(null)
    }
  }

  async function onSyncAll() {
    setBusyId('sync-all')
    setError(null)
    try {
      const r = await syncAllProviderModels()
      setMsg(fmt(c.syncAllSuccess, { new: r.total_new }))
      await reload()
    } catch (err) {
      setError(String(err))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-6 space-y-4 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">{c.title}</h3>
        <button
          type="button"
          disabled={busyId === 'sync-all'}
          onClick={onSyncAll}
          className="text-xs rounded border px-2 py-1 hover:bg-stone-50 disabled:opacity-50"
        >
          {c.syncAll}
        </button>
      </div>

      {status && (
        <div className="text-xs text-stone-600 space-y-1">
          <p>
            {c.encryption}:{' '}
            {status.encryption_configured ? c.encryptionOk : c.encryptionMissing}
          </p>
          <p className="flex flex-wrap gap-2">
            {Object.entries(status.configured || {}).map(([p, ok]) => (
              <span
                key={p}
                className={`rounded px-2 py-0.5 ${ok ? 'bg-green-100 text-green-800' : 'bg-stone-100'}`}
              >
                {p}: {status.source?.[p] || (ok ? 'ok' : 'none')}
              </span>
            ))}
          </p>
        </div>
      )}

      {error && <p className="text-red-700 text-xs">{error}</p>}
      {msg && <p className="text-stone-600 text-xs">{msg}</p>}

      <ul className="divide-y rounded border">
        {items.length === 0 ? (
          <li className="p-3 text-stone-500">{c.noCredentials}</li>
        ) : (
          items.map((cred) => (
            <li key={cred.id} className="p-3 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="font-medium">{cred.name}</span>
                  <span className="ml-2 text-stone-500">{cred.provider}</span>
                  <span className="ml-2 text-xs text-stone-400">
                    {cred.model_count} {c.models}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busyId === cred.id}
                    onClick={() => onDiscover(cred.id)}
                    className="text-xs text-amber-700 hover:underline disabled:opacity-50"
                  >
                    {busyId === cred.id ? c.discovering : c.discover}
                  </button>
                  <button
                    type="button"
                    disabled={busyId === cred.id}
                    onClick={() => onRegisterAll(cred)}
                    className="text-xs text-amber-700 hover:underline disabled:opacity-50"
                  >
                    {c.registerAll}
                  </button>
                  <button
                    type="button"
                    disabled={busyId === `sync-${cred.provider}`}
                    onClick={() => onSyncProvider(cred.provider)}
                    className="text-xs text-stone-600 hover:underline disabled:opacity-50"
                  >
                    {c.syncProvider}
                  </button>
                  <button type="button" onClick={() => onTest(cred.id)} className="text-xs text-amber-700 hover:underline">
                    {t.common.test}
                  </button>
                  <button type="button" onClick={() => onDelete(cred.id)} className="text-xs text-red-600 hover:underline">
                    {t.common.delete}
                  </button>
                </div>
              </div>
              {discovered[cred.id]?.length ? (
                <ul className="text-xs text-stone-500 pl-2 border-l-2 border-stone-200 max-h-24 overflow-y-auto">
                  {discovered[cred.id].map((m) => (
                    <li key={m.name}>
                      {m.name}
                      {m.model_type ? ` (${m.model_type})` : ''}
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))
        )}
      </ul>

      <form onSubmit={onAdd} className="grid gap-2 sm:grid-cols-2">
        <input
          className="rounded border px-3 py-2"
          placeholder={c.name}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <select className="rounded border px-3 py-2" value={provider} onChange={(e) => setProvider(e.target.value)}>
          {PROVIDERS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        {provider === 'ollama' && (
          <input
            className="rounded border px-3 py-2 sm:col-span-2"
            placeholder={c.baseUrl}
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
          />
        )}
        {provider !== 'ollama' && (
          <input
            className="rounded border px-3 py-2 sm:col-span-2"
            type="password"
            placeholder={c.apiKey}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
        )}
        <button type="submit" className="sm:col-span-2 rounded bg-stone-800 px-3 py-2 text-white">
          {c.add}
        </button>
      </form>
    </section>
  )
}
