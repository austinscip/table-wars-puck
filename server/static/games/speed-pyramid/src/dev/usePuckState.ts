// PROTOTYPE — Virtual Puck state machine + polling. Mirrors the firmware
// state machine (g_speed_pyramid.h) and the polling cadence documented in
// docs/adr/0002-virtual-puck-mirrors-firmware-polling.md. Shared by all
// three UI variants under ./variants/.
//
// Throwaway scope: lean MVP per CONTEXT.md ## Sandbox / dev tooling.
//   - Pair / lobby / category-pick / minigame fire / question+answer /
//     reveal / match-end + reset.
//   - No active power-up use, no sabotage targeting (defer to v1.1).

import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'

export type Letter = 'A' | 'B' | 'C' | 'D'

export type PuckState =
  | { kind: 'IDLE' }
  | { kind: 'PAIR_REQUESTING' }
  // Host-only intermediate. Pragmatic input model: we don't actually
  // tilt-cycle 6 digits; confirmCode() auto-POSTs all 6 + /pair/confirm.
  | { kind: 'PAIR_DIALING'; pair_code: string }
  | { kind: 'PAIR_CONFIRMING' }
  | {
      kind: 'LOBBY_WAITING'
      pair_code: string
      is_host: boolean
      session_code?: string
    }
  | { kind: 'IN_GAME_IDLE'; session_code: string }
  | {
      kind: 'IN_GAME_ANSWERING'
      session_code: string
      question_id: number
      started_at: number // epoch ms (server-authoritative start time)
      pending?: Letter // tilt has been moved, not yet locked
    }
  | {
      kind: 'IN_GAME_LOCKED'
      session_code: string
      question_id: number
      chosen: Letter
    }
  | { kind: 'CATEGORY_PICKING'; session_code: string; offer: CategoryOffer[] }
  | { kind: 'MINIGAME'; session_code: string; kind_name: string }
  | { kind: 'MATCH_ENDED'; session_code: string }
  | { kind: 'ERROR'; msg: string }

interface CategoryOffer {
  id: number
  name: string
  emoji: string
  question_count: number
}

interface CurrentQuestionResp {
  active: boolean
  question_id?: number
  started_at?: number
}

interface MatchStateResp {
  complete: boolean
  round?: number
  total_rounds?: number
}

// Post helpers — minimal, prototype error handling (swallow + log).
async function POST<T>(path: string, body: unknown = {}): Promise<T | null> {
  try {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!r.ok) {
      console.warn('POST', path, r.status)
      return null
    }
    const text = await r.text()
    return text ? (JSON.parse(text) as T) : ({} as T)
  } catch (e) {
    console.warn('POST err', path, e)
    return null
  }
}

async function GET<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(path)
    if (!r.ok) return null
    return (await r.json()) as T
  } catch {
    return null
  }
}

export function usePuckState(puck_id: number) {
  const [state, setState] = useState<PuckState>({ kind: 'IDLE' })
  const stateRef = useRef(state)
  stateRef.current = state

  // ---- Actions (mirror firmware events) ----

  const hold1s = useCallback(async () => {
    const cur = stateRef.current
    if (cur.kind !== 'IDLE') return
    setState({ kind: 'PAIR_REQUESTING' })
    const resp = await POST<{
      role: 'host' | 'joiner'
      pair_code: string
      lobby_code: string | null
    }>('/api/pair/request', { puck_id })
    if (!resp) {
      setState({ kind: 'ERROR', msg: 'pair/request failed' })
      return
    }
    if (resp.role === 'host') {
      setState({ kind: 'PAIR_DIALING', pair_code: resp.pair_code })
    } else {
      // Joiner: server already added us. Confirm to finalize join.
      await POST('/api/pair/confirm', { puck_id, code: resp.pair_code })
      setState({
        kind: 'LOBBY_WAITING',
        pair_code: resp.pair_code,
        is_host: false,
      })
    }
  }, [puck_id])

  const hold3s = useCallback(async () => {
    const cur = stateRef.current
    // Cancel pair or leave match.
    if (
      cur.kind === 'PAIR_DIALING' ||
      cur.kind === 'PAIR_CONFIRMING' ||
      cur.kind === 'LOBBY_WAITING'
    ) {
      await POST('/api/pair/cancel', { puck_id })
      setState({ kind: 'IDLE' })
    } else if (
      cur.kind === 'IN_GAME_IDLE' ||
      cur.kind === 'IN_GAME_LOCKED' ||
      cur.kind === 'IN_GAME_ANSWERING' ||
      cur.kind === 'MATCH_ENDED' ||
      cur.kind === 'CATEGORY_PICKING' ||
      cur.kind === 'MINIGAME'
    ) {
      await POST('/api/sp/leave-match', { puck_id })
      setState({ kind: 'IDLE' })
    }
  }, [puck_id])

  // Pragmatic dial short-circuit: server already sent us pair_code. We
  // POST each of the 6 digits to /api/pair/dial then /api/pair/confirm.
  const confirmCode = useCallback(async () => {
    const cur = stateRef.current
    if (cur.kind !== 'PAIR_DIALING') return
    setState({ kind: 'PAIR_CONFIRMING' })
    const code = cur.pair_code
    for (let i = 0; i < 6; i++) {
      const digit = parseInt(code[i] ?? '0', 10)
      await api.pair.dial(puck_id, i, digit)
    }
    const resp = await api.pair.confirm(puck_id, code)
    if (!resp) {
      setState({ kind: 'ERROR', msg: 'confirm failed' })
      return
    }
    setState({
      kind: 'LOBBY_WAITING',
      pair_code: code,
      is_host: true,
    })
  }, [puck_id])

  const tap = useCallback(async () => {
    const cur = stateRef.current
    if (cur.kind === 'LOBBY_WAITING' && cur.is_host) {
      const resp = await api.pair.start(puck_id)
      if (resp?.ok && resp.session_code) {
        setState({
          kind: 'LOBBY_WAITING',
          pair_code: cur.pair_code,
          is_host: true,
          session_code: resp.session_code,
        })
      }
    } else if (cur.kind === 'IN_GAME_ANSWERING') {
      // Lock the currently-pending answer (or A as default if user hasn't
      // tilted). Mirrors firmware: TAP in IN_GAME_ANSWERING.
      const letter = cur.pending ?? 'A'
      const elapsed_ms = Math.max(0, Date.now() - cur.started_at)
      await POST('/api/sp/answer', {
        session_code: cur.session_code,
        puck_id,
        question_id: cur.question_id,
        answer: letter,
        response_time_ms: Math.round(elapsed_ms),
      })
      setState({
        kind: 'IN_GAME_LOCKED',
        session_code: cur.session_code,
        question_id: cur.question_id,
        chosen: letter,
      })
    } else if (cur.kind === 'MATCH_ENDED') {
      await api.sp.reset(cur.session_code)
      setState({ kind: 'IN_GAME_IDLE', session_code: cur.session_code })
    } else if (cur.kind === 'MINIGAME') {
      // Lean MVP: minigame TAP = fire with A quadrant + a mid-time t_ms.
      // Good enough to clear the phase; aim accuracy isn't the bug we're
      // chasing here. Firmware tilt-aim would be wired in v1.1.
      await POST('/api/sp/minigame/fire', {
        session_code: cur.session_code,
        puck_id,
        t_ms: 2500,
        quadrant: 'A',
      })
    }
  }, [puck_id])

  // Tilt sets the "pending" letter while in IN_GAME_ANSWERING; otherwise
  // currently a no-op (dial doesn't use tilt under pragmatic model).
  const tilt = useCallback((dir: 'N' | 'E' | 'S' | 'W') => {
    const cur = stateRef.current
    if (cur.kind !== 'IN_GAME_ANSWERING') return
    const map: Record<typeof dir, Letter> = { N: 'A', E: 'B', S: 'C', W: 'D' }
    const letter = map[dir]
    setState({ ...cur, pending: letter })
    // Best-effort preview broadcast.
    void POST('/api/trivia/answer-preview', {
      session_code: cur.session_code,
      puck_id,
      answer: letter,
    })
  }, [puck_id])

  // Convenience: pick an answer letter directly (button-click in
  // variants that expose A/B/C/D as discrete pills).
  const selectAnswer = useCallback(
    (letter: Letter) => {
      const cur = stateRef.current
      if (cur.kind !== 'IN_GAME_ANSWERING') return
      setState({ ...cur, pending: letter })
      void POST('/api/trivia/answer-preview', {
        session_code: cur.session_code,
        puck_id,
        answer: letter,
      })
    },
    [puck_id],
  )

  // Atomic pick-and-lock for the variants' single-click ABCD buttons.
  // Doing selectAnswer() then tap() in two calls is racy: setState is
  // async, so tap reads the stale stateRef.pending and posts 'A'
  // regardless of what the user clicked. This action takes the letter
  // directly so the POST always reflects the click.
  const lockAnswer = useCallback(
    async (letter: Letter) => {
      const cur = stateRef.current
      if (cur.kind !== 'IN_GAME_ANSWERING') return
      const elapsed_ms = Math.max(0, Date.now() - cur.started_at)
      // Optimistic preview so other clients see the chosen letter.
      setState({ ...cur, pending: letter })
      void POST('/api/trivia/answer-preview', {
        session_code: cur.session_code,
        puck_id,
        answer: letter,
      })
      await POST('/api/sp/answer', {
        session_code: cur.session_code,
        puck_id,
        question_id: cur.question_id,
        answer: letter,
        response_time_ms: Math.round(elapsed_ms),
      })
      setState({
        kind: 'IN_GAME_LOCKED',
        session_code: cur.session_code,
        question_id: cur.question_id,
        chosen: letter,
      })
    },
    [puck_id],
  )

  // Category picker (only available if this puck is the picker).
  const pickCategory = useCallback(
    async (category_id: number) => {
      const cur = stateRef.current
      if (cur.kind !== 'CATEGORY_PICKING') return
      await POST(`/api/sp/select-category/${cur.session_code}`, {
        puck_id,
        category_id,
      })
    },
    [puck_id],
  )

  // ---- Polling (state-dependent) ----
  useEffect(() => {
    let cancelled = false
    let timer: number | undefined

    async function tick() {
      if (cancelled) return
      const cur = stateRef.current

      if (cur.kind === 'LOBBY_WAITING') {
        const lobby = await GET<{ code: string; started: boolean; session_code: string | null }>(
          '/api/pair/lobby-state',
        )
        if (!cancelled && lobby?.started && lobby.session_code) {
          setState({
            kind: 'IN_GAME_IDLE',
            session_code: lobby.session_code,
          })
        }
      } else if (
        cur.kind === 'IN_GAME_IDLE' ||
        cur.kind === 'IN_GAME_LOCKED' ||
        cur.kind === 'CATEGORY_PICKING' ||
        cur.kind === 'MINIGAME'
      ) {
        const sc = cur.session_code
        // First check match end.
        const ms = await GET<MatchStateResp>(`/api/sp/match-state/${sc}`)
        if (!cancelled && ms?.complete) {
          setState({ kind: 'MATCH_ENDED', session_code: sc })
          // Fall through so polling keeps ticking. After "Play again"
          // (tap in MATCH_ENDED) the puck transitions to IN_GAME_IDLE
          // and the next tick needs to detect the new question. If we
          // `return`ed here the timer would die and the second match
          // would never advance past the lobby state.
        }
        // Then check current question. If active and we're not already
        // answering it, transition into ANSWERING.
        const cq = await GET<CurrentQuestionResp>(
          `/api/sp/current-question/${sc}`,
        )
        if (cancelled) return
        if (cq?.active && cq.question_id) {
          const already =
            cur.kind === 'IN_GAME_LOCKED' && cur.question_id === cq.question_id
          if (!already) {
            setState({
              kind: 'IN_GAME_ANSWERING',
              session_code: sc,
              question_id: cq.question_id,
              started_at: (cq.started_at ?? Date.now() / 1000) * 1000,
            })
            // Fall through to schedule next tick. An earlier version
            // `return`ed here, which killed the polling timer — the
            // puck never noticed Q2 because the effect only re-runs on
            // [puck_id] change. Hub Q2 lock was unreachable.
          }
        }
        // NOTE: pucks must NOT POST /api/sp/load-question. That endpoint
        // both ADVANCES state and returns the new question — the TV calls
        // it. Real firmware pucks never call it, they only poll read-only
        // endpoints. Earlier versions of this hook called load-question
        // from each puck's polling loop, which caused state["round"] to
        // increment twice (one per polling puck) and matches to start on
        // round 2 with the category pick skipped. See:
        // pair_routes.py sp_load_question — `state["round"] = next_round`
        // runs unconditionally on every POST.
      } else if (cur.kind === 'IN_GAME_ANSWERING') {
        // Watch for the question rotating under us (reveal happened,
        // server moved on, but we haven't tapped). Drop to LOCKED.
        const sc = cur.session_code
        const cq = await GET<CurrentQuestionResp>(
          `/api/sp/current-question/${sc}`,
        )
        if (cancelled) return
        if (!cq?.active || cq.question_id !== cur.question_id) {
          // Server says active=false. Either the question rotated, OR
          // the match ended while we were mid-answer. Use the `complete`
          // flag the server includes on a complete-match response to
          // skip straight to MATCH_ENDED instead of LOCKED.
          if (cq && (cq as { complete?: boolean }).complete) {
            setState({ kind: 'MATCH_ENDED', session_code: sc })
          } else {
            setState({
              kind: 'IN_GAME_LOCKED',
              session_code: sc,
              question_id: cur.question_id,
              chosen: cur.pending ?? 'A',
            })
          }
        }
      } else if (cur.kind === 'MATCH_ENDED') {
        // Detect a "Play again" issued by another puck. The server's
        // sp_reset clears SP state + _QUESTION_TRACKER, so match-state
        // flips back to complete=false. Drop to IN_GAME_IDLE and let
        // the normal IDLE branch pick up the new question on the next
        // tick. Without this branch, the joining puck stays stuck on
        // the final scoreboard while the host has already moved on.
        const sc = cur.session_code
        const ms = await GET<MatchStateResp>(`/api/sp/match-state/${sc}`)
        if (cancelled) return
        if (ms && ms.complete === false) {
          setState({ kind: 'IN_GAME_IDLE', session_code: sc })
        }
      }

      // Schedule next tick. Cadence per faithful-polling decision.
      const nextDelayMs =
        stateRef.current.kind === 'LOBBY_WAITING' ? 1000 : 500
      timer = window.setTimeout(tick, nextDelayMs)
    }

    timer = window.setTimeout(tick, 100)
    return () => {
      cancelled = true
      if (timer) window.clearTimeout(timer)
    }
  }, [puck_id])

  return {
    state,
    actions: {
      tap,
      hold1s,
      hold3s,
      tilt,
      confirmCode,
      selectAnswer,
      lockAnswer,
      pickCategory,
    },
  }
}
