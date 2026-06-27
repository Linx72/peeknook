import { useCallback, useEffect, useState } from 'react'
import { getShipStatus, type ShipStatus } from '../api'
import VpsDeployHints from './VpsDeployHints'
import { useI18n } from '../i18n'
import { fmt } from '../i18n/format'

export default function ShipChecklist() {
  const { t } = useI18n()
  const s = t.shipChecklist
  const [status, setStatus] = useState<ShipStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState<string | null>(null)

  const reload = useCallback(() => {
    setLoading(true)
    getShipStatus()
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  async function copyText(text: string, key: string) {
    await navigator.clipboard.writeText(text)
    setCopied(key)
    setTimeout(() => setCopied(null), 2000)
  }

  if (loading && !status) {
    return (
      <section className="rounded-xl border border-stone-200 bg-white p-6 text-sm text-stone-500">
        {s.loading}
      </section>
    )
  }

  const gateLabel = (id: string) => {
    const key = id as keyof typeof s.gates
    return s.gates[key] ?? id
  }

  const done = status?.gates_done ?? 0
  const total = status?.gates_total ?? 0

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-6 space-y-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">{s.title}</h3>
        <div className="flex gap-2">
          <button type="button" onClick={reload} className="text-xs text-stone-500 underline">
            {s.refresh}
          </button>
          <button
            type="button"
            onClick={() => copyText('./scripts/peeknook-manual-gates.sh', 'wizard')}
            className="text-xs text-amber-700 underline"
          >
            {copied === 'wizard' ? s.copied : s.copyWizard}
          </button>
          <button
            type="button"
            onClick={() => copyText('./scripts/peeknook-do-all.sh', 'doall')}
            className="text-xs text-amber-700 underline"
          >
            {copied === 'doall' ? s.copied : s.copyDoAll}
          </button>
        </div>
      </div>
      {total > 0 && (
        <p className="text-xs text-stone-500">{fmt(s.progress, { done, total, version: status?.version ?? '?' })}</p>
      )}
      <p className="text-xs text-stone-500">{s.hint}</p>
      <ul className="space-y-2">
        {status?.gates.map((g) => (
          <li key={g.id} className="flex items-start gap-2">
            <span className={g.done ? 'text-emerald-600' : 'text-stone-400'}>{g.done ? '✓' : '○'}</span>
            <span className="flex-1">
              {gateLabel(g.id)}
              {!g.done && g.command && (
                <button
                  type="button"
                  className="block text-left text-xs text-amber-700 underline font-mono mt-0.5"
                  onClick={() => copyText(g.command!, g.id)}
                >
                  {copied === g.id ? s.copied : g.command}
                </button>
              )}
            </span>
          </li>
        ))}
      </ul>
      {status && !status.vps_prod && (
        <VpsDeployHints show />
      )}
      {!status?.stripe_live && status?.cloud_health?.ok && (
        <p className="text-xs text-stone-500">
          {status.stripe_webhook ? s.stripeWebhookOk : s.stripeDevHint}
        </p>
      )}
      {status?.deploy_pack_ready === false && (
        <p className="text-xs text-stone-500 font-mono">{s.deployPackHint}</p>
      )}
      {status?.handoff.available && (
        <p className="text-xs text-amber-800 bg-amber-50 rounded p-2">
          {s.handoffReady}: {status.handoff.source_id}
        </p>
      )}
    </section>
  )
}
