// API helpers for talking to the Flask backend.
// Uses relative URLs so the same bundle works against the dev server
// (localhost:5001), Railway (tablewars.up.railway.app), or any custom
// domain without rebuild.

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = ''
    try {
      detail = JSON.stringify(await res.json())
    } catch {
      detail = await res.text()
    }
    throw new Error(`POST ${path} -> ${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

export interface PairRequestResponse {
  pair_code: string
  expires_at: number
  reused: boolean
}

export interface PairConfirmResponse {
  puck_id: number
  session_code: string
}

export const api = {
  pair: {
    request: (puck_id: number) =>
      postJson<PairRequestResponse>('/api/pair/request', { puck_id }),

    dial: (puck_id: number, digit_index: number, digit: number) =>
      postJson<{ accepted: boolean; progress: (number | null)[] }>(
        '/api/pair/dial',
        { puck_id, digit_index, digit },
      ),

    confirm: (puck_id: number, code: string) =>
      postJson<PairConfirmResponse>('/api/pair/confirm', { puck_id, code }),
  },
}
