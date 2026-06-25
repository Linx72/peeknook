import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getShipStatus } from '../api'
import { useI18n } from '../i18n'
import { fmt } from '../i18n/format'

export default function ShipStatusBanner() {
  const { t } = useI18n()
  const b = t.shipBanner
  const [done, setDone] = useState<number | null>(null)
  const [total, setTotal] = useState<number | null>(null)
  const [version, setVersion] = useState<string | null>(null)

  useEffect(() => {
    getShipStatus()
      .then((s) => {
        setDone(s.gates_done ?? null)
        setTotal(s.gates_total ?? null)
        setVersion(s.version ?? null)
      })
      .catch(() => {
        setDone(null)
        setTotal(null)
      })
  }, [])

  if (done === null || total === null) return null

  const allDone = done >= total

  return (
    <section
      className={`rounded-xl border p-4 text-sm flex flex-wrap items-center justify-between gap-3 ${
        allDone ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-stone-200 bg-stone-50 text-stone-800'
      }`}
    >
      <p>
        {allDone
          ? fmt(b.allDone, { version: version ?? '?' })
          : fmt(b.progress, { done, total, version: version ?? '?' })}
      </p>
      {!allDone && (
        <Link to="/settings" className="text-xs font-medium underline">
          {b.openChecklist}
        </Link>
      )}
    </section>
  )
}
