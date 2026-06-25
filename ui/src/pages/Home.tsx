import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getSetupStatus, type SetupStatus } from '../api'
import { useI18n } from '../i18n'

export default function Home() {
  const { t } = useI18n()
  const h = t.home
  const [status, setStatus] = useState<SetupStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getSetupStatus()
      .then(setStatus)
      .catch((e) => setError(String(e)))
  }, [])

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-stone-200 bg-white p-8 shadow-sm">
        <h1 className="text-3xl font-bold">{h.title}</h1>
        <p className="mt-2 max-w-xl text-stone-600">{h.subtitle}</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            to="/notebooks"
            className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
          >
            {h.openNotebooks}
          </Link>
          <Link
            to="/search"
            className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium hover:bg-stone-100"
          >
            {t.nav.search}
          </Link>
          <Link
            to="/cloud"
            className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium hover:bg-stone-100"
          >
            {t.nav.cloud}
          </Link>
          <Link
            to="/transformations"
            className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium hover:bg-stone-100"
          >
            {t.nav.transform}
          </Link>
          <Link
            to="/podcasts"
            className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium hover:bg-stone-100"
          >
            {t.nav.podcasts}
          </Link>
          <Link
            to="/settings"
            className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium hover:bg-stone-100"
          >
            {h.setup}
          </Link>
          <a
            href="https://github.com/Linx72/peeknook/releases/latest"
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-900 hover:bg-amber-100"
          >
            {h.downloadDesktop}
          </a>
        </div>
      </section>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {h.apiUnavailable} <code className="font-mono">./scripts/peeknook-backend.sh</code>
        </div>
      )}

      {status && (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Stat label={h.ollama} value={status.ollama_configured ? h.connected : h.notFound} />
          <Stat label={h.models} value={String(status.model_count)} />
          <Stat label={h.notebooks} value={String(status.notebook_count)} />
          <Stat label={h.syncQueue} value={String(status.sync_pending)} />
          <Stat
            label={h.cloud}
            value={status.cloud_configured ? h.cloudOk : h.cloudOff}
          />
        </section>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-stone-200 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-stone-500">{label}</div>
      <div className="mt-1 text-xl font-semibold">{value}</div>
    </div>
  )
}
