import { useEffect, useState } from 'react'
import { getSyncConflicts, type SyncConflict } from '../api'
import { useI18n } from '../i18n'

export default function SyncConflictsPanel() {
  const { t } = useI18n()
  const c = t.settings.conflicts
  const [rows, setRows] = useState<SyncConflict[]>([])

  useEffect(() => {
    getSyncConflicts().then(setRows).catch(() => setRows([]))
  }, [])

  if (rows.length === 0) return null

  return (
    <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm space-y-2">
      <h3 className="font-semibold text-amber-900">{c.title}</h3>
      <ul className="space-y-1 text-xs text-amber-900">
        {rows.slice(0, 10).map((r) => (
          <li key={r.id} className="font-mono">
            {r.object_type}:{r.object_id} — {r.resolution}
          </li>
        ))}
      </ul>
      {rows.length > 10 && <p className="text-xs text-amber-700">{c.more}</p>}
    </section>
  )
}
