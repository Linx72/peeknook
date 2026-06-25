import { useCallback, useEffect, useState } from 'react'
import DefaultModelsSettings from '../components/DefaultModelsSettings'
import AppUpdater from '../components/AppUpdater'
import ModelCredentials from '../components/ModelCredentials'
import {
  getOllamaStatus,
  getPeeknookSettings,
  getSetupStatus,
  getSyncStatus,
  runSyncNow,
  updatePeeknookSettings,
  type OllamaStatus,
  type PeeknookSettings,
  type SetupStatus,
} from '../api'
import { useI18n } from '../i18n'
import { fmt } from '../i18n/format'

export default function Settings() {
  const { t } = useI18n()
  const s = t.settings
  const [status, setStatus] = useState<SetupStatus | null>(null)
  const [settings, setSettings] = useState<PeeknookSettings | null>(null)
  const [ollama, setOllama] = useState<OllamaStatus | null>(null)
  const [syncStatus, setSyncStatus] = useState<Record<string, unknown> | null>(null)
  const [cloudUrl, setCloudUrl] = useState('')
  const [msg, setMsg] = useState<string | null>(null)

  const reload = useCallback(async () => {
    const [st, s, o, sync] = await Promise.all([
      getSetupStatus(),
      getPeeknookSettings(),
      getOllamaStatus(),
      getSyncStatus(),
    ])
    setStatus(st)
    setSettings(s)
    setOllama(o)
    setSyncStatus(sync)
    if (s.cloud_url) setCloudUrl(s.cloud_url)
  }, [])

  useEffect(() => {
    reload().catch(() => setStatus(null))
  }, [reload])

  async function saveAutoSync(auto: boolean) {
    await updatePeeknookSettings({ auto_sync: auto, cloud_url: cloudUrl || settings?.cloud_url })
    setMsg(auto ? s.autoSyncOn : s.autoSyncOff)
    reload()
  }

  async function syncNow() {
    setMsg(s.syncing)
    try {
      const r = await runSyncNow()
      setMsg(fmt(s.syncOk, { pushed: r.push?.pushed ?? 0, pulled: r.pull?.applied ?? 0 }))
    } catch (e) {
      setMsg(String(e))
    }
    reload()
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">{s.title}</h2>

      <section className="rounded-xl border border-stone-200 bg-white p-6 space-y-3 text-sm">
        <Row label={s.product} value={s.productValue} />
        <Row label={s.notebooks} value={String(status?.notebook_count ?? 0)} />
        <Row
          label={s.ollama}
          value={
            ollama?.reachable
              ? fmt(s.ollamaReachable, { url: ollama.url, count: ollama.model_count ?? 0 })
              : fmt(s.ollamaUnreachable, { hint: ollama?.hint || 'ollama serve' })
          }
        />
        {!ollama?.reachable && (
          <p className="text-amber-800 bg-amber-50 rounded p-2 text-xs">{s.ollamaHint}</p>
        )}
        <Row label={s.pendingSync} value={String(status?.sync_pending ?? 0)} />
        <Row label={s.lastSync} value={String(settings?.last_sync_at ?? syncStatus?.last_sync_at ?? '—')} />
        <Row label={s.syncStatus} value={String(settings?.last_sync_status ?? syncStatus?.last_sync_status ?? '—')} />
      </section>

      <ModelCredentials />
      <DefaultModelsSettings />
      <AppUpdater />

      <section className="rounded-xl border border-stone-200 bg-white p-6 space-y-4 text-sm">
        <h3 className="font-semibold">{s.cloudSync}</h3>
        <input
          className="w-full rounded border border-stone-300 px-3 py-2"
          placeholder={s.cloudUrl}
          value={cloudUrl}
          onChange={(e) => setCloudUrl(e.target.value)}
        />
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={settings?.auto_sync ?? false}
            onChange={(e) => saveAutoSync(e.target.checked)}
          />
          {fmt(s.autoSync, { sec: settings?.auto_sync_interval_sec ?? 300 })}
        </label>
        <button type="button" onClick={syncNow} className="rounded bg-amber-600 px-3 py-2 text-white">
          {s.syncNow}
        </button>
        {msg && <p className="text-stone-600">{msg}</p>}
      </section>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:justify-between">
      <span className="text-stone-500">{label}</span>
      <span className="font-mono text-stone-800 break-all">{value}</span>
    </div>
  )
}
