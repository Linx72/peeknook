import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 600000,
})

export type SetupStatus = {
  product: string
  ollama_configured: boolean
  ollama_url: string | null
  model_count: number
  notebook_count: number
  sync_pending: number
  auto_sync?: boolean
  e2e_sync?: boolean
  cloud_configured?: boolean
  cloud_url?: string | null
}

export type CloudHealth = {
  configured: boolean
  ok: boolean
  url?: string
  version?: string
  status?: string
  error?: string
}

export type PeeknookSettings = {
  cloud_url?: string
  auto_sync: boolean
  auto_sync_interval_sec: number
  e2e_sync: boolean
  has_token: boolean
  last_sync_at?: string
  last_sync_status?: string
}

export type SourceStatus = {
  status: string | null
  message: string
  command_id?: string | null
}

export type Notebook = {
  id: string
  name: string
  description?: string
  source_count?: number
}

export type Source = {
  id: string
  title?: string
  topics?: string[]
  asset?: { file_path?: string; url?: string }
  embedded?: boolean
  created?: string
  updated?: string
}

export type ChatMessage = {
  id: string
  type: 'human' | 'ai' | string
  content: string
  timestamp?: string | null
}

export type ChatSession = {
  id: string
  title: string
  notebook_id?: string
  message_count?: number
}

export async function getSetupStatus(): Promise<SetupStatus> {
  const { data } = await api.get<SetupStatus>('/peeknook/setup-status')
  return data
}

export async function getCloudHealth(): Promise<CloudHealth> {
  const { data } = await api.get<CloudHealth>('/peeknook/cloud-health')
  return data
}

export type ShipGate = { id: string; done: boolean; automated: boolean }

export type ShipStatus = {
  physical_two_mac: { done: boolean; completed_at?: string; source_id?: string }
  handoff: { available: boolean; source_id?: string }
  cloud_health: CloudHealth
  stripe_live?: boolean
  deploy_pack_ready?: boolean
  vps_prod?: boolean
  gates: ShipGate[]
}

export async function getShipStatus(): Promise<ShipStatus> {
  const { data } = await api.get<ShipStatus>('/peeknook/ship-status')
  return data
}

export type BillingConfig = { stripe_live: boolean; stripe_webhook: boolean }

export async function getBillingConfig(cloudUrl: string): Promise<BillingConfig> {
  const { data } = await axios.get<BillingConfig>(`${cloudUrl.replace(/\/$/, '')}/billing/config`)
  return data
}

export async function listNotebooks(): Promise<Notebook[]> {
  const { data } = await api.get<Notebook[]>('/notebooks')
  return data
}

export async function getNotebook(id: string): Promise<Notebook> {
  const { data } = await api.get<Notebook>(`/notebooks/${id}`)
  return data
}

export async function createNotebook(name: string, description: string): Promise<Notebook> {
  const { data } = await api.post<Notebook>('/notebooks', { name, description })
  return data
}

export async function listSources(notebookId: string): Promise<Source[]> {
  const { data } = await api.get<Source[]>('/sources', { params: { notebook_id: notebookId } })
  return data
}

export async function getSourceStatus(sourceId: string): Promise<SourceStatus> {
  const { data } = await api.get<SourceStatus>(`/sources/${sourceId}/status`)
  return data
}

export type TwoMacHandoff = {
  available: boolean
  source_id?: string
  notebook_id?: string
  cloud_url?: string
  cloud_email?: string
}

export type SyncConflict = {
  id: string
  object_type: string
  object_id: string
  resolution: string
  detail_json?: string | null
  created_at?: string
}

export async function getSyncConflicts(limit = 20): Promise<SyncConflict[]> {
  const { data } = await api.get<SyncConflict[]>('/peeknook/sync/conflicts', { params: { limit } })
  return data
}

export async function getTwoMacHandoff(): Promise<TwoMacHandoff> {
  const { data } = await api.get<TwoMacHandoff>('/peeknook/two-mac-handoff')
  return data
}

export async function getPeeknookSettings(): Promise<PeeknookSettings> {
  const { data } = await api.get<PeeknookSettings>('/peeknook/settings')
  return data
}

export async function updatePeeknookSettings(body: Partial<PeeknookSettings & { cloud_token?: string }>) {
  const { data } = await api.put('/peeknook/settings', body)
  return data
}

export async function runSyncNow() {
  const { data } = await api.post('/peeknook/sync/run')
  return data
}

export async function uploadPdf(notebookId: string, file: File, title?: string): Promise<Source> {
  const form = new FormData()
  form.append('type', 'upload')
  form.append('notebook_id', notebookId)
  form.append('notebooks', JSON.stringify([notebookId]))
  form.append('file', file)
  form.append('title', title || file.name)
  form.append('embed', 'true')
  form.append('async_processing', 'true')
  form.append('delete_source', 'false')
  const { data } = await api.post<Source>('/sources', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listChatSessions(notebookId: string): Promise<ChatSession[]> {
  const { data } = await api.get<ChatSession[]>('/chat/sessions', { params: { notebook_id: notebookId } })
  return data
}

export async function createChatSession(notebookId: string, title: string): Promise<ChatSession> {
  const { data } = await api.post<ChatSession>('/chat/sessions', { notebook_id: notebookId, title })
  return data
}

export async function buildChatContext(notebookId: string, sourceIds: string[]) {
  const context_config = {
    sources: Object.fromEntries(sourceIds.map((id) => [id, 'full content'])),
    notes: {} as Record<string, string>,
  }
  const { data } = await api.post<{ context: Record<string, unknown>; token_count: number }>(
    '/chat/context',
    { notebook_id: notebookId, context_config },
  )
  return data
}

export async function sendChatMessage(
  sessionId: string,
  message: string,
  context: Record<string, unknown>,
) {
  const { data } = await api.post<{ session_id: string; messages: ChatMessage[] }>('/chat/execute', {
    session_id: sessionId,
    message,
    context,
  })
  return data
}

export async function streamChatMessage(
  sessionId: string,
  message: string,
  context: Record<string, unknown>,
  onEvent: (event: { type: string; content?: string; message?: string }) => void,
): Promise<void> {
  const res = await fetch('/api/chat/execute/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, context }),
  })
  if (!res.ok || !res.body) throw new Error(`Chat stream failed: ${res.status}`)
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        onEvent(JSON.parse(line.slice(6)))
      } catch {
        /* ignore partial */
      }
    }
  }
}

export type Note = {
  id: string
  title?: string
  content?: string
  note_type?: string
  created?: string
  updated?: string
}

export async function listNotes(notebookId: string): Promise<Note[]> {
  const { data } = await api.get<Note[]>('/notes', { params: { notebook_id: notebookId } })
  return data
}

export async function createNote(notebookId: string, title: string, content: string): Promise<Note> {
  const { data } = await api.post<Note>('/notes', {
    notebook_id: notebookId,
    title,
    content,
    note_type: 'human',
  })
  return data
}

export async function deleteNote(noteId: string) {
  await api.delete(`/notes/${noteId}`)
}

export type SearchHit = { id?: string; title?: string; content?: string; parent_id?: string; type?: string }

export async function searchKnowledge(
  query: string,
  limit = 20,
  type: 'text' | 'vector' = 'text',
) {
  const { data } = await api.post<{ results: SearchHit[]; total_count: number }>('/search', {
    query,
    type,
    limit,
    search_sources: true,
    search_notes: true,
  })
  return data
}

export type OllamaStatus = {
  reachable: boolean
  url: string
  model_count?: number
  models?: string[]
  error?: string
  hint?: string
}

export async function getOllamaStatus(): Promise<OllamaStatus> {
  const { data } = await api.get<OllamaStatus>('/peeknook/ollama/status')
  return data
}

export async function getSyncStatus() {
  const { data } = await api.get('/peeknook/sync/status')
  return data
}

export type CloudAuth = { access_token: string; token_type: string }

export async function cloudRegister(email: string, password: string, cloudUrl: string): Promise<CloudAuth> {
  const { data } = await axios.post<CloudAuth>(`${cloudUrl}/auth/register`, { email, password })
  return data
}

export async function cloudLogin(email: string, password: string, cloudUrl: string): Promise<CloudAuth> {
  const { data } = await axios.post<CloudAuth>(`${cloudUrl}/auth/login`, { email, password })
  return data
}

export async function pushSyncToCloud(token: string, cloudUrl: string) {
  const { data } = await api.post('/peeknook/sync/push', { cloud_url: cloudUrl, token })
  return data
}

export async function pullSyncFromCloud(token: string, cloudUrl: string) {
  const { data } = await api.post('/peeknook/sync/pull', { cloud_url: cloudUrl, token })
  return data
}

export type Transformation = {
  id: string
  name: string
  title?: string
  description?: string
  prompt?: string
}

export type Model = {
  id: string
  name: string
  provider: string
  type: string
}

export async function listTransformations(): Promise<Transformation[]> {
  const { data } = await api.get<Transformation[]>('/transformations')
  return data
}

export async function executeTransformation(transformationId: string, inputText: string, modelId: string) {
  const { data } = await api.post<{ output: string }>('/transformations/execute', {
    transformation_id: transformationId,
    input_text: inputText,
    model_id: modelId,
  })
  return data
}

export async function listModels(type?: string): Promise<Model[]> {
  const { data } = await api.get<Model[]>('/models', { params: type ? { type } : undefined })
  return data
}

export async function getDefaultModels() {
  const { data } = await api.get<{
    default_chat_model?: string
    default_transformation_model?: string
    default_embedding_model?: string
  }>('/models/defaults')
  return data
}

export async function updateDefaultModels(body: {
  default_chat_model?: string | null
  default_transformation_model?: string | null
  default_embedding_model?: string | null
}) {
  const { data } = await api.put('/models/defaults', body)
  return data
}

export type Credential = {
  id: string
  name: string
  provider: string
  modalities: string[]
  model_count: number
  has_api_key: boolean
}

export type CredentialsStatus = {
  encryption_configured?: boolean
  configured?: Record<string, boolean>
  source?: Record<string, string>
}

export async function getCredentialsStatus(): Promise<CredentialsStatus> {
  const { data } = await api.get<CredentialsStatus>('/credentials/status')
  return data
}

export async function listCredentials(): Promise<Credential[]> {
  const { data } = await api.get<Credential[]>('/credentials')
  return data
}

export async function createCredential(body: {
  name: string
  provider: string
  modalities?: string[]
  api_key?: string
  base_url?: string
}) {
  const { data } = await api.post<Credential>('/credentials', body)
  return data
}

export async function deleteCredential(id: string) {
  await api.delete(`/credentials/${id}`)
}

export async function testCredential(id: string) {
  const { data } = await api.post<{ status?: string; message?: string }>(`/credentials/${id}/test`)
  return data
}

export type DiscoveredModel = {
  name: string
  provider: string
  model_type?: string | null
  description?: string | null
}

export async function discoverCredentialModels(credentialId: string) {
  const { data } = await api.post<{
    credential_id: string
    provider: string
    discovered: DiscoveredModel[]
  }>(`/credentials/${credentialId}/discover`)
  return data
}

export async function registerCredentialModels(
  credentialId: string,
  models: Array<{ name: string; provider: string; model_type: string }>,
) {
  const { data } = await api.post<{ created: number; existing: number }>(
    `/credentials/${credentialId}/register-models`,
    { models },
  )
  return data
}

export async function syncProviderModels(provider: string) {
  const { data } = await api.post<{ provider: string; discovered: number; new: number; existing: number }>(
    `/models/sync/${provider}`,
  )
  return data
}

export async function syncAllProviderModels() {
  const { data } = await api.post<{
    total_discovered: number
    total_new: number
    results: Record<string, { provider: string; discovered: number; new: number; existing: number }>
  }>('/models/sync')
  return data
}

export async function createTransformation(body: {
  name: string
  title: string
  description: string
  prompt: string
  apply_default?: boolean
}) {
  const { data } = await api.post<Transformation>('/transformations', body)
  return data
}

export async function deleteTransformation(id: string) {
  await api.delete(`/transformations/${id}`)
}

export type EpisodeProfile = {
  id: string
  name: string
  description: string
  speaker_config: string
  default_briefing: string
  num_segments: number
  outline_llm?: string | null
  transcript_llm?: string | null
  language?: string | null
}

export type SpeakerProfile = {
  id: string
  name: string
  description: string
  voice_model?: string | null
  speakers: Array<Record<string, string>>
}
export type PodcastEpisode = {
  id: string
  name: string
  job_status?: string
  audio_url?: string
  error_message?: string
  created?: string
}

export async function listEpisodeProfiles(): Promise<EpisodeProfile[]> {
  const { data } = await api.get<EpisodeProfile[]>('/episode-profiles')
  return data
}

export async function listSpeakerProfiles(): Promise<SpeakerProfile[]> {
  const { data } = await api.get<SpeakerProfile[]>('/speaker-profiles')
  return data
}

export async function listPodcastEpisodes(): Promise<PodcastEpisode[]> {
  const { data } = await api.get<PodcastEpisode[]>('/podcasts/episodes')
  return data
}

export async function generatePodcast(body: {
  episode_profile: string
  speaker_profile: string
  episode_name: string
  content?: string
  notebook_id?: string
}) {
  const { data } = await api.post<{ job_id: string; status: string; message: string }>(
    '/podcasts/generate',
    body,
  )
  return data
}

export async function getPodcastJobStatus(jobId: string) {
  const { data } = await api.get(`/podcasts/jobs/${jobId}`)
  return data
}

export async function createSpeakerProfile(body: {
  name: string
  description?: string
  speakers: Array<Record<string, string>>
  voice_model?: string
}) {
  const { data } = await api.post<SpeakerProfile>('/speaker-profiles', body)
  return data
}

export async function deleteSpeakerProfile(id: string) {
  await api.delete(`/speaker-profiles/${id}`)
}

export async function createEpisodeProfile(body: {
  name: string
  description?: string
  speaker_config: string
  default_briefing: string
  num_segments?: number
  outline_llm?: string
  transcript_llm?: string
}) {
  const { data } = await api.post<EpisodeProfile>('/episode-profiles', body)
  return data
}

export async function deleteEpisodeProfile(id: string) {
  await api.delete(`/episode-profiles/${id}`)
}

export default api
