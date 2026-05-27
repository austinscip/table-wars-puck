import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../lib/api'
import { getSocket } from '../lib/socket'
import { audio } from '../lib/audio'

/**
 * Slice E1 — Category pick phase.
 *
 * The picker (per server policy: round-1 = lowest puck_id, otherwise
 * previous round's winner) chooses 1 of 3 random categories. Other
 * pucks watch. 10-second deadline; if no pick lands by then, the
 * server auto-defaults to the first offer and emits `category_picked`.
 *
 * The TV navigates here when `loadQuestion(sc)` returns `phase:
 * 'category_pick'`. It subscribes to `category_offer` (refresh) and
 * `category_picked` (navigate back to /question/<sc> and let
 * QuestionScreen re-issue loadQuestion to receive the actual question).
 */

interface CategoryOffer {
  id: number
  name: string
  emoji: string
  question_count: number
}

interface CategoryPickState {
  picker_puck_id: number
  offer: CategoryOffer[]
  deadline_at: number
  started_at: number
  round: number
}

export default function CategoryPickScreen() {
  const navigate = useNavigate()
  const { sessionCode } = useParams<{ sessionCode: string }>()
  const [pick, setPick] = useState<CategoryPickState | null>(null)
  const [chosenId, setChosenId] = useState<number | null>(null)
  const [remainingMs, setRemainingMs] = useState(10_000)
  // R024: guards the one-shot deadline kick (see countdown effect).
  const kickedRef = useRef(false)

  // Bootstrap the pick state via REST (idempotent: load-question
  // returns the same pending pick on every call). Subscribe to
  // category_offer / category_picked sockets.
  useEffect(() => {
    if (!sessionCode) return
    const sc = sessionCode
    const socket = getSocket()
    socket.emit('join_session_room', { session_code: sc })

    let alive = true
    api.sp
      .loadQuestion(sc)
      .then((resp) => {
        if (!alive) return
        if ((resp as unknown as { phase?: string }).phase === 'category_pick') {
          const p = resp as unknown as CategoryPickState
          setPick({
            picker_puck_id: p.picker_puck_id,
            offer: p.offer,
            deadline_at: p.deadline_at,
            started_at: p.started_at,
            round: p.round,
          })
          // R018: audio cue when the pick screen opens.
          audio.pickShow()
        } else {
          // Pick already resolved by the time we got here.
          navigate(`/question/${sc}`, { replace: true })
        }
      })
      .catch(() => {})

    function onOffer(p: CategoryPickState & { session_code: string }) {
      if (p.session_code !== sc) return
      setPick(p)
    }
    function onPicked(p: { session_code: string; category_id: number }) {
      if (p.session_code !== sc) return
      setChosenId(p.category_id)
      // R018: audio cue when the pick locks in (either by picker or
      // by 10s auto-default).
      audio.pickLocked()
      // Hand off to QuestionScreen after a brief reveal beat.
      window.setTimeout(() => navigate(`/question/${sc}`, { replace: true }), 1100)
    }
    socket.on('category_offer', onOffer)
    socket.on('category_picked', onPicked)
    return () => {
      alive = false
      socket.off('category_offer', onOffer)
      socket.off('category_picked', onPicked)
    }
  }, [sessionCode, navigate])

  // Tick the countdown so the picker sees the deadline.
  useEffect(() => {
    if (!pick || !sessionCode) return
    const sc = sessionCode
    const tick = () => {
      const ms = Math.max(0, pick.deadline_at * 1000 - Date.now())
      setRemainingMs(ms)
      // R024: when the deadline expires with no pick locked in, the TV
      // MUST re-issue loadQuestion. The server only auto-defaults the
      // category (and advances to the question) when load-question is
      // called after the deadline — and pucks never call it (ADR-0002).
      // Without this kick, nobody calls load-question on a timeout, the
      // server never auto-resolves, and the match hangs at 0s forever.
      if (ms <= 0 && chosenId === null && !kickedRef.current) {
        kickedRef.current = true
        api.sp
          .loadQuestion(sc)
          .then((resp) => {
            const phase = (resp as unknown as { phase?: string }).phase
            if (phase === 'category_pick') {
              // Server clock hasn't passed the deadline yet (skew) —
              // allow the next tick to retry rather than navigating into
              // a still-pending pick.
              kickedRef.current = false
            } else {
              navigate(`/question/${sc}`, { replace: true })
            }
          })
          .catch(() => {
            kickedRef.current = false
          })
      }
    }
    tick()
    const id = window.setInterval(tick, 100)
    return () => window.clearInterval(id)
  }, [pick, chosenId, sessionCode, navigate])

  if (!pick) {
    return (
      <main className="flex h-full w-full items-center justify-center">
        <p className="font-body text-2xl text-text/60">Loading pick…</p>
      </main>
    )
  }

  return (
    <main className="flex h-full w-full flex-col items-center justify-center gap-10 px-12 py-12">
      <div className="flex flex-col items-center gap-2">
        <span className="font-body text-base font-medium uppercase tracking-widest text-text/40">
          Round {pick.round} · Category Pick
        </span>
        <motion.h1
          initial={{ scale: 0.7, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, ease: [0.34, 1.56, 0.64, 1] }}
          className="font-display text-[clamp(2.5rem,6vw,5rem)] leading-none text-primary"
        >
          PUCK {pick.picker_puck_id} PICKS
        </motion.h1>
        <span className="font-mono text-3xl text-accent">
          {Math.ceil(remainingMs / 1000)}s
        </span>
      </div>

      <div className="grid w-full max-w-6xl grid-cols-3 gap-6">
        <AnimatePresence>
          {pick.offer.map((cat, i) => {
            const isChosen = chosenId === cat.id
            const dimmed = chosenId !== null && !isChosen
            return (
              <motion.div
                key={cat.id}
                layout
                initial={{ y: 30, opacity: 0 }}
                animate={{
                  y: 0,
                  opacity: dimmed ? 0.3 : 1,
                  scale: isChosen ? 1.08 : 1,
                }}
                exit={{ y: -30, opacity: 0 }}
                transition={{
                  duration: 0.45,
                  delay: 0.12 * i,
                  ease: [0.34, 1.56, 0.64, 1],
                }}
                className={`flex flex-col items-center gap-4 rounded-3xl border-2 ${
                  isChosen
                    ? 'border-correct'
                    : 'border-text/15'
                } bg-text/5 p-8`}
                style={
                  isChosen
                    ? { boxShadow: '0 0 60px rgba(251,191,36,0.55)' }
                    : undefined
                }
              >
                <span className="text-[clamp(4rem,10vw,9rem)] leading-none">
                  {cat.emoji}
                </span>
                <span className="text-center font-display text-[clamp(1.25rem,2.5vw,2.5rem)] leading-tight text-text">
                  {cat.name}
                </span>
                <span className="font-body text-base text-text/50">
                  {cat.question_count} question
                  {cat.question_count === 1 ? '' : 's'}
                </span>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
        className="font-body text-xl text-text/50"
      >
        {chosenId === null
          ? `Waiting on Puck ${pick.picker_puck_id}…`
          : 'Locked in! Loading…'}
      </motion.div>
    </main>
  )
}
