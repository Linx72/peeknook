import { useEffect, useState } from 'react'
import axios from 'axios'
import { getBillingConfig } from '../api'
import { useI18n } from '../i18n'
import { fmt } from '../i18n/format'

const CLOUD_KEY = 'peeknook_cloud_url'
const TOKEN_KEY = 'peeknook_cloud_token'

type Plan = { id: string; name: string; price_usd: number; storage_bytes: number; sync_events_month: number }
type Subscription = {
  plan_id: string
  plan: Plan
  status: string
  usage: {
    storage_bytes: number
    storage_limit_bytes: number
    sync_events_month: number
    sync_limit_month: number
  }
}

function fmtBytes(n: number) {
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 / 1024 / 1024).toFixed(1)} GB`
}

export default function Billing() {
  const { t } = useI18n()
  const b = t.billing
  const cloudUrl = localStorage.getItem(CLOUD_KEY) || 'http://127.0.0.1:8090'
  const token = localStorage.getItem(TOKEN_KEY) || ''
  const [plans, setPlans] = useState<Plan[]>([])
  const [sub, setSub] = useState<Subscription | null>(null)
  const [stripeLive, setStripeLive] = useState<boolean | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  const headers = token ? { Authorization: `Bearer ${token}` } : {}

  useEffect(() => {
    axios.get(`${cloudUrl}/billing/plans`).then((r) => setPlans(r.data.plans)).catch(() => setPlans([]))
    getBillingConfig(cloudUrl)
      .then((c) => setStripeLive(c.stripe_live))
      .catch(() => setStripeLive(null))
    if (token) {
      axios
        .get<Subscription>(`${cloudUrl}/billing/subscription`, { headers })
        .then((r) => setSub(r.data))
        .catch(() => setSub(null))
    }
  }, [cloudUrl, token])

  async function upgrade(planId: string) {
    if (!token) return setMsg(b.loginFirst)
    try {
      const { data } = await axios.post<{ message?: string; checkout_url?: string | null; upgraded?: boolean }>(
        `${cloudUrl}/billing/checkout`,
        { plan_id: planId },
        { headers },
      )
      if (data.checkout_url) {
        window.open(data.checkout_url, '_blank', 'noopener')
        setMsg(b.openingCheckout)
        return
      }
      setMsg(data.message || b.upgraded)
      const s = await axios.get<Subscription>(`${cloudUrl}/billing/subscription`, { headers })
      setSub(s.data)
    } catch (e) {
      setMsg(String(e))
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">{b.title}</h2>

      {stripeLive !== null && (
        <p className="text-xs text-stone-500">
          {stripeLive ? b.stripeLive : b.stripeDev}
        </p>
      )}

      {sub && (
        <section className="rounded-xl border bg-white p-4 text-sm space-y-2">
          <p>
            {b.currentPlan}: <strong>{sub.plan.name}</strong> ({sub.status})
          </p>
          <p>
            {b.storage}: {fmtBytes(sub.usage.storage_bytes)} / {fmtBytes(sub.usage.storage_limit_bytes)}
          </p>
          <p>
            {b.syncEvents}: {sub.usage.sync_events_month} / {sub.usage.sync_limit_month}
          </p>
        </section>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        {plans.map((p) => (
          <div key={p.id} className="rounded-xl border bg-white p-4">
            <h3 className="font-semibold">{p.name}</h3>
            <p className="text-2xl font-bold mt-1">
              ${p.price_usd}
              <span className="text-sm font-normal">{b.perMonth}</span>
            </p>
            <ul className="mt-3 text-xs text-stone-600 space-y-1">
              <li>{fmt(b.storageItem, { size: fmtBytes(p.storage_bytes) })}</li>
              <li>{fmt(b.syncItem, { count: p.sync_events_month.toLocaleString() })}</li>
            </ul>
            {p.id !== 'free' && (
              <button
                type="button"
                disabled={sub?.plan_id === p.id}
                onClick={() => upgrade(p.id)}
                className="mt-4 w-full rounded bg-amber-600 py-2 text-sm text-white disabled:opacity-50"
              >
                {sub?.plan_id === p.id ? b.current : b.upgrade}
              </button>
            )}
          </div>
        ))}
      </div>
      {msg && <p className="text-sm">{msg}</p>}
    </div>
  )
}
