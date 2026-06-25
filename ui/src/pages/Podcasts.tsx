import { type FormEvent, useCallback, useEffect, useState } from 'react'
import PodcastProfileEditor from '../components/PodcastProfileEditor'
import { useI18n } from '../i18n'
import { fmt } from '../i18n/format'
import {
  generatePodcast,
  getPodcastJobStatus,
  listEpisodeProfiles,
  listPodcastEpisodes,
  listSpeakerProfiles,
  type EpisodeProfile,
  type PodcastEpisode,
  type SpeakerProfile,
} from '../api'

export default function Podcasts() {
  const { t } = useI18n()
  const [tab, setTab] = useState<'generate' | 'profiles'>('generate')
  const [episodes, setEpisodes] = useState<PodcastEpisode[]>([])
  const [episodeProfiles, setEpisodeProfiles] = useState<EpisodeProfile[]>([])
  const [speakerProfiles, setSpeakerProfiles] = useState<SpeakerProfile[]>([])
  const [episodeProfile, setEpisodeProfile] = useState('')
  const [speakerProfile, setSpeakerProfile] = useState('')
  const [episodeName, setEpisodeName] = useState('')
  const [content, setContent] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const reload = useCallback(async () => {
    const [eps, ep, sp] = await Promise.all([
      listPodcastEpisodes(),
      listEpisodeProfiles(),
      listSpeakerProfiles(),
    ])
    setEpisodes(eps)
    setEpisodeProfiles(ep)
    setSpeakerProfiles(sp)
    if (ep.length && !episodeProfile) setEpisodeProfile(ep[0].name)
    if (sp.length && !speakerProfile) setSpeakerProfile(sp[0].name)
  }, [episodeProfile, speakerProfile])

  useEffect(() => {
    reload().catch((e) => setError(String(e)))
  }, [reload])

  async function onGenerate(e: FormEvent) {
    e.preventDefault()
    if (!episodeProfile || !speakerProfile || !episodeName.trim()) return
    setBusy(true)
    setError(null)
    setMsg(null)
    try {
      const r = await generatePodcast({
        episode_profile: episodeProfile,
        speaker_profile: speakerProfile,
        episode_name: episodeName.trim(),
        content: content.trim() || undefined,
      })
      setMsg(r.message)
      const poll = async () => {
        const st = await getPodcastJobStatus(r.job_id)
        if (st.status === 'completed' || st.status === 'failed') {
          await reload()
          setMsg(
            st.status === 'completed'
              ? t.podcasts.episodeReady
              : fmt(t.podcasts.failed, { reason: st.error_message || 'unknown' }),
          )
          return
        }
        setTimeout(poll, 4000)
      }
      setTimeout(poll, 3000)
    } catch (err) {
      setError(String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">{t.podcasts.title}</h2>
      <p className="text-sm text-stone-600">{t.podcasts.subtitle}</p>

      <div className="flex gap-2 text-sm">
        <button
          type="button"
          onClick={() => setTab('generate')}
          className={`rounded-lg px-3 py-1.5 ${tab === 'generate' ? 'bg-amber-600 text-white' : 'bg-stone-200'}`}
        >
          {t.podcasts.tabGenerate}
        </button>
        <button
          type="button"
          onClick={() => setTab('profiles')}
          className={`rounded-lg px-3 py-1.5 ${tab === 'profiles' ? 'bg-amber-600 text-white' : 'bg-stone-200'}`}
        >
          {t.podcasts.tabProfiles}
        </button>
      </div>

      {error && <p className="text-sm text-red-700">{error}</p>}
      {msg && <p className="text-sm text-stone-700">{msg}</p>}

      {tab === 'profiles' ? (
        <PodcastProfileEditor
          episodeProfiles={episodeProfiles}
          speakerProfiles={speakerProfiles}
          onChanged={reload}
        />
      ) : (
        <>
          <form onSubmit={onGenerate} className="space-y-3 rounded-xl border bg-white p-4 text-sm">
            <label className="block">
              {t.podcasts.form.episodeProfile}
              <select
                className="mt-1 w-full rounded border px-3 py-2"
                value={episodeProfile}
                onChange={(e) => setEpisodeProfile(e.target.value)}
              >
                {episodeProfiles.map((prof) => (
                  <option key={prof.id} value={prof.name}>
                    {prof.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              {t.podcasts.form.speakerProfile}
              <select
                className="mt-1 w-full rounded border px-3 py-2"
                value={speakerProfile}
                onChange={(e) => setSpeakerProfile(e.target.value)}
              >
                {speakerProfiles.map((prof) => (
                  <option key={prof.id} value={prof.name}>
                    {prof.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              {t.podcasts.form.episodeName}
              <input
                className="mt-1 w-full rounded border px-3 py-2"
                value={episodeName}
                onChange={(e) => setEpisodeName(e.target.value)}
                placeholder={t.podcasts.form.episodeNamePlaceholder}
              />
            </label>
            <label className="block">
              {t.podcasts.form.content}
              <textarea
                className="mt-1 w-full rounded border px-3 py-2"
                rows={4}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder={t.podcasts.form.contentPlaceholder}
              />
            </label>
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-amber-600 px-4 py-2 text-white disabled:opacity-50"
            >
              {busy ? t.podcasts.form.submitting : t.podcasts.generate}
            </button>
          </form>

          <section className="rounded-xl border bg-white divide-y">
            <h3 className="p-4 font-semibold text-sm">{t.podcasts.episodes}</h3>
            {episodes.length === 0 ? (
              <p className="p-4 text-sm text-stone-500">{t.podcasts.form.noEpisodes}</p>
            ) : (
              episodes.map((ep) => (
                <div key={ep.id} className="p-4 text-sm flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="font-medium">{ep.name}</div>
                    <div className="text-stone-500">{ep.job_status || t.podcasts.form.unknownStatus}</div>
                  </div>
                  {ep.audio_url && <audio controls src={ep.audio_url} className="max-w-xs" />}
                </div>
              ))
            )}
          </section>
        </>
      )}
    </div>
  )
}
