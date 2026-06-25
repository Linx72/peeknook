import { useEffect, useState } from 'react'
import { useI18n } from '../i18n'
import { assetsFromManifest, fallbackAssets, fetchLatestRelease } from '../lib/releaseAssets'

export default function ReleaseDownloads() {
  const { t } = useI18n()
  const d = t.downloads
  const [assets, setAssets] = useState(fallbackAssets())

  useEffect(() => {
    fetchLatestRelease().then((m) => {
      if (m?.version) setAssets(assetsFromManifest(m))
    })
  }, [])

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-6 space-y-3 text-sm">
      <h3 className="font-semibold">{d.title}</h3>
      <p className="text-stone-500 text-xs">{d.hint}</p>
      <p className="text-xs text-stone-400">{d.versionLabel}: v{assets.version}</p>
      <ul className="space-y-2">
        <li>
          <a className="text-amber-700 underline" href={assets.macos}>
            {d.macos}
          </a>
        </li>
        <li>
          <a className="text-amber-700 underline" href={assets.windowsExe}>
            {d.windowsExe}
          </a>
        </li>
        <li>
          <a className="text-amber-700 underline" href={assets.windowsMsi}>
            {d.windowsMsi}
          </a>
        </li>
      </ul>
      <a className="text-xs text-stone-500 underline" href={assets.releasesPage} target="_blank" rel="noreferrer">
        {d.allReleases}
      </a>
    </section>
  )
}
