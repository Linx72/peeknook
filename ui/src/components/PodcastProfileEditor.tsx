import { type FormEvent, useEffect, useState } from 'react'
import {
  createEpisodeProfile,
  createSpeakerProfile,
  deleteEpisodeProfile,
  deleteSpeakerProfile,
  type EpisodeProfile,
  type SpeakerProfile,
} from '../api'
import { useI18n } from '../i18n'
import { fmt } from '../i18n/format'

type Props = {
  episodeProfiles: EpisodeProfile[]
  speakerProfiles: SpeakerProfile[]
  onChanged: () => Promise<void>
}

export default function PodcastProfileEditor({ episodeProfiles, speakerProfiles, onChanged }: Props) {
  const { t } = useI18n()
  const p = t.podcasts.profiles
  const [spName, setSpName] = useState('')
  const [spDesc, setSpDesc] = useState('')
  const [hostName, setHostName] = useState('')
  const [epName, setEpName] = useState('')
  const [epDesc, setEpDesc] = useState('')
  const [epSpeaker, setEpSpeaker] = useState('')
  const [epBriefing, setEpBriefing] = useState('')
  const [epSegments, setEpSegments] = useState(5)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!hostName) setHostName(p.defaultHost)
    if (!epBriefing) setEpBriefing(p.defaultBriefingValue)
  }, [p.defaultHost, p.defaultBriefingValue, hostName, epBriefing])

  async function onCreateSpeaker(e: FormEvent) {
    e.preventDefault()
    if (!spName.trim()) return
    setError(null)
    try {
      await createSpeakerProfile({
        name: spName.trim(),
        description: spDesc.trim(),
        speakers: [
          {
            name: hostName.trim() || p.defaultHost,
            voice_id: 'default',
            backstory: 'Knowledgeable podcast host',
            personality: 'Clear and engaging',
          },
        ],
      })
      setSpName('')
      setSpDesc('')
      await onChanged()
    } catch (err) {
      setError(String(err))
    }
  }

  async function onCreateEpisode(e: FormEvent) {
    e.preventDefault()
    if (!epName.trim() || !epSpeaker) return
    setError(null)
    try {
      await createEpisodeProfile({
        name: epName.trim(),
        description: epDesc.trim(),
        speaker_config: epSpeaker,
        default_briefing: epBriefing.trim() || p.defaultBriefingValue,
        num_segments: epSegments,
      })
      setEpName('')
      setEpDesc('')
      await onChanged()
    } catch (err) {
      setError(String(err))
    }
  }

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-red-700">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border bg-white p-4 space-y-3 text-sm">
          <h3 className="font-semibold">{t.podcasts.speakerProfiles}</h3>
          <ul className="divide-y">
            {speakerProfiles.map((profile) => (
              <li key={profile.id} className="py-2 flex justify-between gap-2">
                <div>
                  <div className="font-medium">{profile.name}</div>
                  <div className="text-stone-500 text-xs">{profile.description}</div>
                </div>
                <button
                  type="button"
                  className="text-red-600 text-xs"
                  onClick={() => deleteSpeakerProfile(profile.id).then(onChanged)}
                >
                  {t.common.delete}
                </button>
              </li>
            ))}
          </ul>
          <form onSubmit={onCreateSpeaker} className="space-y-2 border-t pt-3">
            <input
              className="w-full rounded border px-3 py-2"
              placeholder={p.profileName}
              value={spName}
              onChange={(e) => setSpName(e.target.value)}
            />
            <input
              className="w-full rounded border px-3 py-2"
              placeholder={p.description}
              value={spDesc}
              onChange={(e) => setSpDesc(e.target.value)}
            />
            <input
              className="w-full rounded border px-3 py-2"
              placeholder={p.hostName}
              value={hostName}
              onChange={(e) => setHostName(e.target.value)}
            />
            <button type="submit" className="rounded bg-stone-800 px-3 py-2 text-white">
              {t.podcasts.createSpeaker}
            </button>
          </form>
        </section>

        <section className="rounded-xl border bg-white p-4 space-y-3 text-sm">
          <h3 className="font-semibold">{t.podcasts.episodeProfiles}</h3>
          <ul className="divide-y">
            {episodeProfiles.map((profile) => (
              <li key={profile.id} className="py-2 flex justify-between gap-2">
                <div>
                  <div className="font-medium">{profile.name}</div>
                  <div className="text-stone-500 text-xs">
                    {fmt(p.speakerMeta, { speaker: profile.speaker_config, count: profile.num_segments })}
                  </div>
                </div>
                <button
                  type="button"
                  className="text-red-600 text-xs"
                  onClick={() => deleteEpisodeProfile(profile.id).then(onChanged)}
                >
                  {t.common.delete}
                </button>
              </li>
            ))}
          </ul>
          <form onSubmit={onCreateEpisode} className="space-y-2 border-t pt-3">
            <input
              className="w-full rounded border px-3 py-2"
              placeholder={p.profileName}
              value={epName}
              onChange={(e) => setEpName(e.target.value)}
            />
            <select
              className="w-full rounded border px-3 py-2"
              value={epSpeaker || speakerProfiles[0]?.name || ''}
              onChange={(e) => setEpSpeaker(e.target.value)}
            >
              <option value="">{p.selectSpeaker}</option>
              {speakerProfiles.map((profile) => (
                <option key={profile.id} value={profile.name}>
                  {profile.name}
                </option>
              ))}
            </select>
            <textarea
              className="w-full rounded border px-3 py-2"
              rows={2}
              placeholder={p.defaultBriefing}
              value={epBriefing}
              onChange={(e) => setEpBriefing(e.target.value)}
            />
            <label className="block text-xs">
              {p.segments}
              <input
                type="number"
                min={1}
                max={12}
                className="mt-1 w-full rounded border px-3 py-2"
                value={epSegments}
                onChange={(e) => setEpSegments(Number(e.target.value))}
              />
            </label>
            <button type="submit" className="rounded bg-stone-800 px-3 py-2 text-white">
              {t.podcasts.createEpisode}
            </button>
          </form>
        </section>
      </div>
    </div>
  )
}
