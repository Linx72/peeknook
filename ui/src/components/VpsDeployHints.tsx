import { useI18n } from '../i18n'

const STEPS = [
  'peeknook-cloud-deploy-pack.sh',
  'PEEKNOOK_VPS_SSH=user@host ./scripts/peeknook-vps-deploy.sh',
  'peeknook-cloud-certbot-hints.sh',
  'Settings → Cloud URL = https://your-domain',
] as const

export default function VpsDeployHints({ show }: { show: boolean }) {
  const { t } = useI18n()
  const v = t.vpsDeploy
  if (!show) return null

  return (
    <section className="rounded-lg border border-stone-200 bg-stone-50 p-3 text-xs space-y-2">
      <p className="font-medium text-stone-800">{v.title}</p>
      <ol className="list-decimal list-inside text-stone-600 space-y-1">
        {STEPS.map((cmd, i) => (
          <li key={cmd}>
            <span className="font-mono text-[11px]">{v.steps[i as keyof typeof v.steps] ?? cmd}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}
