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

export function fallbackAssets(version = '0.2.1') {
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
