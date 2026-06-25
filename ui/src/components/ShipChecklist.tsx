import { useEffect, useState } from 'react'
import { getShipStatus, type ShipStatus } from '../api'
import { useI18n } from '../i18n'

const MANUAL = [
  { id: 'apple_notarize', doc: 'peeknook-apple-secrets-hints.sh' },
  { id: 'vps_deploy', doc: 'peeknook-cloud-deploy-pack.sh' },
  { id: 'stripe_live', doc: 'cloud/.env.prod' },
] as const

export default function ShipChecklist() {
  const { t } = useI18n()
  const s = t.shipChecklist
  const [status, setStatus] = useState<ShipStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getShipStatus()
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
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

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-6 space-y-3 text-sm">
      <h3 className="font-semibold">{s.title}</h3>
      <p className="text-xs text-stone-500">{s.hint}</p>
      <ul className="space-y-2">
        {status?.gates.map((g) => (
          <li key={g.id} className="flex items-start gap-2">
            <span className={g.done ? 'text-emerald-600' : 'text-stone-400'}>{g.done ? '✓' : '○'}</span>
            <span>{gateLabel(g.id)}</span>
          </li>
        ))}
        {MANUAL.map((m) => (
          <li key={m.id} className="flex items-start gap-2">
            <span className="text-stone-400">○</span>
            <span>
              {gateLabel(m.id)}
              <span className="block text-xs text-stone-400 font-mono">{m.doc}</span>
            </span>
          </li>
        ))}
      </ul>
      {status?.handoff.available && (
        <p className="text-xs text-amber-800 bg-amber-50 rounded p-2">
          {s.handoffReady}: {status.handoff.source_id}
        </p>
      )}
    </section>
  )
}
