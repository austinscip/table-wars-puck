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

export interface SpeedPyramidQuestion {
  id: number
  setup: string
  question: string
  answers: { A: string; B: string; C: string; D: string }
  difficulty: string
  time_limit: number
  category: string
  category_emoji: string
}

export interface LoadQuestionResponse {
  question: SpeedPyramidQuestion
  round: number
  total_rounds: number
  started_at: number
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
  sp: {
    loadQuestion: (session_code: string) =>
      postJson<LoadQuestionResponse>(
        `/api/sp/load-question/${session_code}`,
        {},
      ),
    finalResults: async (session_code: string): Promise<FinalResults> => {
      const res = await fetch(`/api/sp/final-results/${session_code}`)
      if (!res.ok) throw new Error(`final-results ${res.status}`)
      return res.json() as Promise<FinalResults>
    },
    reset: (session_code: string) =>
      postJson<{ ok: boolean; session_code: string }>(
        `/api/sp/reset/${session_code}`,
        {},
      ),
  },
}

export interface FinalResultsPlayer {
  puck_id: number
  total: number
  answered: number
  correct: number
  tier: string
}

export interface FinalResults {
  session_code: string
  round: number
  total_rounds: number
  players: FinalResultsPlayer[]
}
