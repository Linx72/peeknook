/** GitHub Releases manifest for desktop download links. */
export const RELEASE_REPO = 'Linx72/peeknook'

export type ReleaseManifest = {
  version: string
  platforms?: Record<string, { url?: string }>
}

export async function fetchLatestRelease(): Promise<ReleaseManifest | null> {
  try {
    const res = await fetch(
      `https://github.com/${RELEASE_REPO}/releases/latest/download/latest.json`,
      { cache: 'no-store' },
    )
    if (!res.ok) return null
    return (await res.json()) as ReleaseManifest
  } catch {
    return null
  }
}

export function fallbackAssets(version = '0.2.5') {
  const tag = `v${version}`
  const base = `https://github.com/${RELEASE_REPO}/releases/download/${tag}`
  return {
    version,
    tag,
    macos: `${base}/PeekNook_${version}_aarch64.dmg`,
    windowsExe: `${base}/PeekNook_${version}_x64-setup.exe`,
    windowsMsi: `${base}/PeekNook_${version}_x64_en-US.msi`,
    releasesPage: `https://github.com/${RELEASE_REPO}/releases/tag/${tag}`,
  }
}

export function assetsFromManifest(m: ReleaseManifest) {
  const v = m.version
  const tag = `v${v}`
  const fb = fallbackAssets(v)
  const win = m.platforms?.['windows-x86_64']?.url
  return {
    version: v,
    tag,
    macos: m.platforms?.['darwin-aarch64']?.url ?? fb.macos,
    windowsExe: win ?? fb.windowsExe,
    windowsMsi: fb.windowsMsi,
    releasesPage: `https://github.com/${RELEASE_REPO}/releases/tag/${tag}`,
  }
}

export type ReleaseNotes = {
  tag: string
  version: string
  body: string
  url: string
  publishedAt?: string
}

export async function fetchLatestReleaseNotes(): Promise<ReleaseNotes | null> {
  try {
    const res = await fetch(`https://api.github.com/repos/${RELEASE_REPO}/releases/latest`, {
      cache: 'no-store',
      headers: { Accept: 'application/vnd.github+json' },
    })
    if (!res.ok) return null
    const data = (await res.json()) as {
      tag_name?: string
      body?: string
      html_url?: string
      published_at?: string
    }
    const tag = data.tag_name ?? ''
    const version = tag.replace(/^v/, '')
    if (!tag || !data.body?.trim()) return null
    return {
      tag,
      version,
      body: data.body.trim(),
      url: data.html_url ?? `https://github.com/${RELEASE_REPO}/releases/latest`,
      publishedAt: data.published_at,
    }
  } catch {
    return null
  }
}
