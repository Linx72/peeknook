import { useEffect, useState } from 'react'
import axios from 'axios'
import { Link } from 'react-router-dom'
import { useI18n } from '../i18n'
import { fmt } from '../i18n/format'

const CLOUD_KEY = 'peeknook_cloud_url'
const TOKEN_KEY = 'peeknook_cloud_token'

type Team = { id: string; name: string; role: string; owner_id: string }

export default function TeamPage() {
  const { t } = useI18n()
  const tm = t.team
  const cloudUrl = localStorage.getItem(CLOUD_KEY) || 'http://127.0.0.1:8090'
  const token = localStorage.getItem(TOKEN_KEY) || ''
  const [teams, setTeams] = useState<Team[]>([])
  const [name, setName] = useState('')
  const [inviteEmail, setInviteEmail] = useState('')
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  const headers = token ? { Authorization: `Bearer ${token}` } : {}

  async function reload() {
    if (!token) return
    const { data } = await axios.get<Team[]>(`${cloudUrl}/teams`, { headers })
    setTeams(data)
  }

  useEffect(() => {
    reload().catch(() => setTeams([]))
  }, [])

  async function createTeam() {
    if (!name.trim() || !token) return
    try {
      await axios.post(`${cloudUrl}/teams`, { name: name.trim() }, { headers })
      setName('')
      setMsg(tm.created)
      reload()
    } catch (e) {
      setMsg(String(e))
    }
  }

  async function invite() {
    if (!selectedTeam || !inviteEmail || !token) return
    try {
      await axios.post(
        `${cloudUrl}/teams/${selectedTeam}/members`,
        { email: inviteEmail, role: 'member' },
        { headers },
      )
      setMsg(fmt(tm.invited, { email: inviteEmail }))
      setInviteEmail('')
    } catch (e) {
      setMsg(String(e))
    }
  }

  if (!token) {
    return (
      <div>
        <h2 className="text-2xl font-bold">{tm.title}</h2>
        <p className="text-sm text-stone-600 mt-2">
          {tm.signInBefore}{' '}
          <Link to="/cloud" className="text-amber-700 underline">
            {tm.cloudLink}
          </Link>{' '}
          {tm.signInAfter}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">{tm.title}</h2>
      <p className="text-sm text-stone-600">{tm.subtitle}</p>

      <section className="rounded-xl border border-stone-200 bg-white p-4 space-y-3 max-w-lg">
        <input
          className="w-full rounded border px-3 py-2 text-sm"
          placeholder={tm.newTeam}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button type="button" onClick={createTeam} className="rounded bg-amber-600 px-3 py-2 text-sm text-white">
          {tm.create}
        </button>
      </section>

      <ul className="divide-y rounded-xl border bg-white">
        {teams.length === 0 ? (
          <li className="p-4 text-sm text-stone-500">{tm.empty}</li>
        ) : (
          teams.map((team) => (
            <li key={team.id} className="flex items-center justify-between p-4">
              <div>
                <div className="font-medium">{team.name}</div>
                <div className="text-xs text-stone-500">{fmt(tm.role, { role: team.role })}</div>
              </div>
              <button type="button" className="text-sm text-amber-700" onClick={() => setSelectedTeam(team.id)}>
                {tm.invite}
              </button>
            </li>
          ))
        )}
      </ul>

      {selectedTeam && (
        <section className="rounded-xl border bg-white p-4 space-y-2 max-w-lg">
          <p className="text-sm font-medium">{tm.inviteTitle}</p>
          <input
            className="w-full rounded border px-3 py-2 text-sm"
            placeholder={tm.inviteEmail}
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
          />
          <button type="button" onClick={invite} className="rounded bg-stone-800 px-3 py-2 text-sm text-white">
            {tm.sendInvite}
          </button>
        </section>
      )}

      {msg && <p className="text-sm text-stone-700">{msg}</p>}
    </div>
  )
}
