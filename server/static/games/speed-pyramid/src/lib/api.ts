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

export type PuckRole = 'host' | 'joiner'

export interface LobbyPlayer {
  puck_id: number
  color: string
  color_name: string
  joined_at: number
  is_host: boolean
}

export interface PairRequestResponse {
  pair_code: string
  role: PuckRole
  color: string
  color_name: string
  host_puck_id: number
  players: LobbyPlayer[]
  expires_at: number
}

export interface PairConfirmResponse {
  role: PuckRole
  color: string
  color_name: string
  players: LobbyPlayer[]
  host_puck_id: number
  lobby_code: string
}

export interface PairStartResponse {
  ok: boolean
  session_code: string
  already_started?: boolean
}

export interface LobbyStateResponse {
  active: boolean
  code?: string
  host_puck_id?: number
  started?: boolean
  session_code?: string | null
  players?: LobbyPlayer[]
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
  expected_pucks?: number[]
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

    preview: (puck_id: number, digit_index: number, digit: number) =>
      postJson<{ ok: boolean }>('/api/pair/preview', {
        puck_id,
        digit_index,
        digit,
      }),

    confirm: (puck_id: number, code: string) =>
      postJson<PairConfirmResponse>('/api/pair/confirm', { puck_id, code }),

    start: (puck_id: number) =>
      postJson<PairStartResponse>('/api/pair/start', { puck_id }),

    lobbyState: async (): Promise<LobbyStateResponse> => {
      const res = await fetch('/api/pair/lobby-state')
      if (!res.ok) throw new Error(`lobby-state ${res.status}`)
      return res.json() as Promise<LobbyStateResponse>
    },
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
    answer: (
      session_code: string,
      puck_id: number,
      question_id: number,
      answer: 'A' | 'B' | 'C' | 'D',
      response_time_ms: number,
    ) =>
      postJson<{
        ok: boolean
        is_correct: boolean
        points: number
        tier: string
        response_time_ms: number
        reveal_emitted: boolean
      }>(`/api/sp/answer`, {
        session_code,
        puck_id,
        question_id,
        answer,
        response_time_ms,
      }),
    forceReveal: (session_code: string) =>
      postJson<{ ok: boolean; emitted: boolean }>(
        `/api/sp/force-reveal/${session_code}`,
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
  color?: string
  color_name?: string
}

export interface FinalResults {
  session_code: string
  round: number
  total_rounds: number
  players: FinalResultsPlayer[]
}
