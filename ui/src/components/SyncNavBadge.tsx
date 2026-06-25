import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getSetupStatus } from '../api'

/** Nav badge when sync events are pending locally. */
export default function SyncNavBadge() {
  const [pending, setPending] = useState(0)

  useEffect(() => {
    let alive = true
    const tick = () => {
      getSetupStatus()
        .then((s) => alive && setPending(s.sync_pending ?? 0))
        .catch(() => alive && setPending(0))
    }
    tick()
    const id = setInterval(tick, 30_000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  if (pending <= 0) return null

  return (
    <Link
      to="/cloud"
      className="rounded-full bg-amber-600 px-2 py-0.5 text-xs font-medium text-white hover:bg-amber-700"
      title="Pending sync"
    >
      {pending}
    </Link>
  )
}
