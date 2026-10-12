import type { Project } from './schema'

/**
 * Turn a failed response into a message worth showing a user.
 *
 * The API answers refusals with a human-readable `detail`. Surfacing the raw
 * body would put JSON braces in the upload panel.
 */
async function failure(res: Response): Promise<Error> {
  const body = await res.text()
  try {
    const parsed = JSON.parse(body) as { detail?: unknown }
    if (typeof parsed.detail === 'string' && parsed.detail) return new Error(parsed.detail)
  } catch {
    // Not JSON — fall through to the body itself.
  }
  return new Error(body || `Request failed (${res.status})`)
}

/**
 * fetch, with an unreachable backend reported as such.
 *
 * When the backend is not running, fetch rejects with a bare TypeError that
 * reaches the user as "Failed to fetch", which names neither the cause nor the
 * service.
 */
async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(path, init)
  } catch {
    throw new Error(
      'Could not reach the transcription service. Is the backend running?',
    )
  }
}

export interface JobStatus {
  id: string
  kind: string
  status: 'queued' | 'running' | 'done' | 'failed'
  stage: string | null
  progress: number
  payload: Record<string, unknown>
  result: Project | null
  error: string | null
}

export interface ExportOptions {
  format: string
  aspect: string
  mode: string
  crf: number
  preset: string
}

export async function uploadMedia(
  file: File,
  language: string,
): Promise<{ job_id: string; asset_id: string }> {
  const form = new FormData()
  form.append('file', file)
  form.append('language', language)
  const res = await request('/api/jobs', { method: 'POST', body: form })
  if (!res.ok) throw await failure(res)
  return (await res.json()) as { job_id: string; asset_id: string }
}

export async function getJob(jobId: string): Promise<JobStatus> {
  const res = await request(`/api/jobs/${jobId}`)
  if (!res.ok) throw await failure(res)
  return (await res.json()) as JobStatus
}

export async function* streamJob(jobId: string): AsyncGenerator<JobStatus> {
  const res = await request(`/api/jobs/${jobId}/events`)
  if (!res.ok || !res.body) throw await failure(res)
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue
      try {
        yield JSON.parse(line.slice(5).trim()) as JobStatus
      } catch {
        // ignore malformed frames
      }
    }
  }
}

export async function exportSubtitle(project: Project, format: string): Promise<string> {
  const res = await request('/api/export/subtitles', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project, format }),
  })
  if (!res.ok) throw await failure(res)
  return res.text()
}

export async function createExport(
  assetId: string,
  project: Project,
  options: ExportOptions,
): Promise<{ job_id: string; export_id: string }> {
  const res = await request('/api/exports', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ asset_id: assetId, project, ...options }),
  })
  if (!res.ok) throw await failure(res)
  return (await res.json()) as { job_id: string; export_id: string }
}

export function exportDownloadUrl(exportId: string): string {
  return `/api/exports/${exportId}/download`
}
