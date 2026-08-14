const BASE = 'https://pharma-complaint-ai.onrender.com'

console.log('API BASE:', BASE)

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }

  return res.status === 204 ? null : res.json()
}

export const api = {
  capabilities: () => request('/intake/capabilities'),
  health: () => request('/health'),
  listSamples: () => request('/intake/samples'),
  readSample: (filename) => request(`/intake/samples/${encodeURIComponent(filename)}`),

  listComplaints: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== '' && v != null),
    ).toString()
    return request(`/complaints${qs ? `?${qs}` : ''}`)
  },
  getComplaint: (id) => request(`/complaints/${id}`),
  createComplaint: (payload) =>
    request('/complaints', { method: 'POST', body: JSON.stringify(payload) }),
  updateComplaint: (id, payload) =>
    request(`/complaints/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteComplaint: (id) => request(`/complaints/${id}`, { method: 'DELETE' }),
  stats: () => request('/complaints/stats'),
  reanalyze: (id) => request(`/intake/reanalyze/${id}`, { method: 'POST' }),

  chat: (payload) => request('/chat', { method: 'POST', body: JSON.stringify(payload) }),
}

/**
 * Drive the SSE extraction endpoints.
 *
 * Uses fetch + a stream reader rather than EventSource because EventSource cannot
 * POST a file body. Calls `onEvent(name, data)` for each server-sent event.
 */
export async function streamExtraction({ file, text, filename, onEvent, signal }) {
  const isUpload = Boolean(file)
  const url = isUpload ? `${BASE}/intake/stream-upload` : `${BASE}/intake/stream`

  let body
  let headers = {}
  if (isUpload) {
    body = new FormData()
    body.append('file', file)
  } else {
    body = JSON.stringify({ text, filename })
    headers = { 'Content-Type': 'application/json' }
  }

  const res = await fetch(url, { method: 'POST', body, headers, signal })

  if (!res.ok) {
    let detail = `Extraction failed (${res.status})`
    try {
      const parsed = await res.json()
      detail = parsed.detail || detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''

    for (const frame of frames) {
      if (!frame.trim()) continue
      let event = 'message'
      const dataLines = []
      for (const line of frame.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
      }
      if (!dataLines.length) continue
      try {
        onEvent(event, JSON.parse(dataLines.join('\n')))
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}
