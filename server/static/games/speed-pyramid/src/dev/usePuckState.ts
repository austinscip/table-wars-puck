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
  | {
      kind: 'MINIGAME'
      session_code: string
      flavor: 'BULLSEYE' | 'SHOT_CLOCK'
      target_quadrant: Letter | null
      started_at: number
      deadline_at: number
      pending_quadrant?: Letter
      fired?: boolean
    }
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
  exists?: boolean
  complete: boolean
  round?: number
  total_rounds?: number
  // Slice E1 — set when the server is in a category-pick phase.
  pending_category_pick?: {
    picker_puck_id: number
    offer: CategoryOffer[]
    deadline_at: number
    started_at: number
  } | null
  // Slice E2 — set when the server is in a minigame phase.
  pending_minigame?: {
    flavor: 'BULLSEYE' | 'SHOT_CLOCK'
    duration_s: number
    target_quadrant: Letter | null
    cycle_ms: number | null
    green_frac: number | null
    started_at: number
    deadline_at: number
  } | null
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
      if (cur.fired) return
      // Slice E2: TAP fires the minigame. BULLSEYE uses the puck's
      // pending_quadrant (set by tilt) or defaults to 'A'; SHOT_CLOCK
      // doesn't need a quadrant — server scores from t_ms only.
      const t_ms = Math.max(0, Date.now() - cur.started_at * 1000)
      const quadrant = cur.flavor === 'BULLSEYE'
        ? (cur.pending_quadrant ?? 'A')
        : null
      setState({ ...cur, fired: true })
      await POST('/api/sp/minigame/fire', {
        session_code: cur.session_code,
        puck_id,
        t_ms: Math.round(t_ms),
        quadrant,
      })
    }
  }, [puck_id])

  // Tilt sets the "pending" letter while in IN_GAME_ANSWERING (or
  // pending_quadrant for BULLSEYE minigames); otherwise a no-op
  // (dial doesn't use tilt under pragmatic model).
  const tilt = useCallback((dir: 'N' | 'E' | 'S' | 'W') => {
    const cur = stateRef.current
    const dirMap: Record<typeof dir, Letter> = { N: 'A', E: 'B', S: 'C', W: 'D' }
    if (cur.kind === 'MINIGAME') {
      if (cur.flavor !== 'BULLSEYE' || cur.fired) return
      setState({ ...cur, pending_quadrant: dirMap[dir] })
      return
    }
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

  // "Back to start" — exposed at MATCH_ENDED as a per-puck affordance
  // for ending the session entirely. Differs from hold3s (which is a
  // per-puck leave-match) in that it ALSO clears the global lobby so
  // the TV navigates back to the title screen instead of getting stuck
  // on the final scoreboard. Same code path as the Hub-level Reset all
  // button — both call /api/pair/clear, server broadcasts the
  // lobby_cancelled socket event, every TV reacts.
  const goBackToStart = useCallback(async () => {
    console.log('[goBackToStart] called', { puck_id })
    try {
      const r = await api.pair.clear()
      console.log('[goBackToStart] api.pair.clear ok', r)
    } catch (e) {
      console.warn('[goBackToStart] api.pair.clear failed', e)
    }
    setState({ kind: 'IDLE' })
    console.log('[goBackToStart] setState IDLE')
  }, [puck_id])

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
        // Slice E1 — if the server is in a category-pick phase,
        // transition every puck to CATEGORY_PICKING with the offer.
        // Only the puck whose puck_id matches picker_puck_id will see
        // its pickCategory action route through; others sit on the
        // screen and watch (or are unmounted server-side from the
        // pick once a pick is locked).
        // No early return: per the pattern set in Slice C fixes,
        // setState then fall through so the polling timer at the
        // bottom keeps scheduling — otherwise the puck would be
        // pinned in CATEGORY_PICKING forever once it entered.
        const pp = ms?.pending_category_pick
        if (!cancelled && pp) {
          const already =
            cur.kind === 'CATEGORY_PICKING' &&
            cur.offer.length === pp.offer.length &&
            cur.offer.every((c, i) => c.id === pp.offer[i].id)
          if (!already) {
            setState({
              kind: 'CATEGORY_PICKING',
              session_code: sc,
              offer: pp.offer,
            })
          }
        } else if (!cancelled && cur.kind === 'CATEGORY_PICKING' && !pp) {
          // Pick resolved — drop to IN_GAME_IDLE; the next tick picks
          // up the new question via current-question.
          setState({ kind: 'IN_GAME_IDLE', session_code: sc })
        }

        // Slice E2 — same pattern for minigame phase.
        const mgp = ms?.pending_minigame
        if (!cancelled && mgp) {
          const already =
            cur.kind === 'MINIGAME' &&
            cur.flavor === mgp.flavor &&
            cur.started_at === mgp.started_at
          if (!already) {
            setState({
              kind: 'MINIGAME',
              session_code: sc,
              flavor: mgp.flavor,
              target_quadrant: mgp.target_quadrant,
              started_at: mgp.started_at,
              deadline_at: mgp.deadline_at,
            })
          }
        } else if (!cancelled && cur.kind === 'MINIGAME' && !mgp) {
          // Minigame resolved — drop to IN_GAME_IDLE.
          setState({ kind: 'IN_GAME_IDLE', session_code: sc })
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
        // Two recovery paths out of MATCH_ENDED, distinguished by
        // /api/sp/match-state's `exists` flag:
        //   - exists=false  -> Hub Reset all or another puck's "Back to
        //                      start" wiped server state entirely. Drop
        //                      to IDLE so the user can re-pair fresh.
        //   - exists=true && complete=false -> another puck hit "Play
        //                      again". Drop to IN_GAME_IDLE and let the
        //                      normal IDLE branch detect the new question.
        //   - exists=true && complete=true -> still on the final
        //                      scoreboard; sit tight.
        const sc = cur.session_code
        const ms = await GET<MatchStateResp>(`/api/sp/match-state/${sc}`)
        if (cancelled) return
        if (ms && ms.exists === false) {
          setState({ kind: 'IDLE' })
        } else if (ms && ms.complete === false) {
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
      goBackToStart,
    },
  }
}
