import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../lib/api'
import { getSocket } from '../lib/socket'
import { audio } from '../lib/audio'
import { clamp } from '../lib/num'
import AmbientBackground from '../components/AmbientBackground'

/**
 * Slice E2 — Minigame phase.
 *
 * Fires between question rounds 2/4/6. Two flavors:
 *
 *   BULLSEYE  — Server picks a target quadrant (A/B/C/D). Pucks
 *               tilt-aim then tap. Score = quadrant match × speed
 *               bonus, 8s window.
 *   SHOT_CLOCK — Sweeping horizontal pointer with a green zone at
 *               center. Tap when pointer is in the zone. Score =
 *               closeness to the green zone center on a 3s cycle.
 *               Total 8s window.
 *
 * The TV runs its OWN visual countdown but server is the source of
 * truth: at deadline + ~1s the TV POSTs /api/sp/minigame/finish to
 * force resolution. On `minigame_winner` socket the TV shows
 * results, then navigates back to /question/<sc> after a short
 * hold for the next round.
 */

interface MinigameStartPayload {
  flavor: 'BULLSEYE' | 'SHOT_CLOCK'
  duration_s: number
  target_quadrant?: 'A' | 'B' | 'C' | 'D' | null
  cycle_ms?: number | null
  green_frac?: number | null
  started_at: number
  deadline_at: number
  round?: number
}

interface MinigameFireEvent {
  session_code: string
  puck_id: number
  t_ms: number
  quadrant?: string | null
  points: number
}

interface MinigameResult {
  puck_id: number
  t_ms: number | null
  quadrant: string | null
  points: number
  bonus: number
  cumulative_total: number
}

interface MinigameWinnerEvent {
  session_code: string
  flavor: 'BULLSEYE' | 'SHOT_CLOCK'
  target_quadrant?: 'A' | 'B' | 'C' | 'D' | null
  results: MinigameResult[]
}

interface MinigameAimPreviewEvent {
  session_code: string
  puck_id: number
  quadrant: 'A' | 'B' | 'C' | 'D' | null
}

// Mirror of server's PUCK_COLORS for per-puck reticle coloring.
const PUCK_COLOR: Record<number, string> = {
  1: '#3B82F6', 2: '#EC4899', 3: '#FBBF24', 4: '#10B981',
  5: '#A855F7', 6: '#F97316', 7: '#06B6D4', 8: '#EF4444',
}

const POST_RESOLVE_HOLD_MS = 2500

export default function MinigameScreen() {
  const navigate = useNavigate()
  const { sessionCode } = useParams<{ sessionCode: string }>()
  const [mg, setMg] = useState<MinigameStartPayload | null>(null)
  const [fires, setFires] = useState<MinigameFireEvent[]>([])
  const [aims, setAims] = useState<Record<number, 'A' | 'B' | 'C' | 'D'>>({})
  const [winner, setWinner] = useState<MinigameWinnerEvent | null>(null)
  const [remainingMs, setRemainingMs] = useState(8_000)
  const finishedRef = useRef(false)

  useEffect(() => {
    if (!sessionCode) return
    const sc = sessionCode
    const socket = getSocket()
    socket.emit('join_session_room', { session_code: sc })

    let alive = true
    api.sp
      .minigameState(sc)
      .then((s) => {
        if (!alive) return
        if (!s.active) {
          navigate(`/question/${sc}`, { replace: true })
          return
        }
        setMg({
          flavor: s.flavor!,
          duration_s: s.duration_s!,
          target_quadrant: s.target_quadrant ?? null,
          cycle_ms: s.cycle_ms ?? null,
          green_frac: s.green_frac ?? null,
          started_at: s.started_at!,
          deadline_at: s.deadline_at!,
        })
      })
      .catch(() => {})

    function onStart(p: MinigameStartPayload & { session_code: string }) {
      if (p.session_code !== sc) return
      setMg(p)
      setFires([])
      setWinner(null)
      finishedRef.current = false
      audio.questionShow()
    }
    function onFire(p: MinigameFireEvent) {
      if (p.session_code !== sc) return
      setFires((prev) => [...prev, p])
      // Once a puck fires, its aim reticle should disappear.
      setAims((prev) => {
        const next = { ...prev }
        delete next[p.puck_id]
        return next
      })
      audio.lockIn()
    }
    function onAimPreview(p: MinigameAimPreviewEvent) {
      if (p.session_code !== sc) return
      setAims((prev) => {
        const next = { ...prev }
        if (p.quadrant) next[p.puck_id] = p.quadrant
        else delete next[p.puck_id]
        return next
      })
    }
    function onWinner(p: MinigameWinnerEvent) {
      if (p.session_code !== sc) return
      setWinner(p)
      const anyScored = p.results.some((r) => r.points > 0)
      if (anyScored) audio.correct()
      else audio.reveal()
      window.setTimeout(() => {
        navigate(`/question/${sc}`, { replace: true })
      }, POST_RESOLVE_HOLD_MS)
    }

    socket.on('minigame_start', onStart)
    socket.on('minigame_fire', onFire)
    socket.on('minigame_winner', onWinner)
    socket.on('minigame_aim_preview', onAimPreview)
    return () => {
      alive = false
      socket.off('minigame_start', onStart)
      socket.off('minigame_fire', onFire)
      socket.off('minigame_winner', onWinner)
      socket.off('minigame_aim_preview', onAimPreview)
    }
  }, [sessionCode, navigate])

  // Visual countdown + auto-finish belt-and-suspenders.
  useEffect(() => {
    if (!mg || !sessionCode) return
    const tick = () => {
      const ms = Math.max(0, mg.deadline_at * 1000 - Date.now())
      setRemainingMs(ms)
      if (ms === 0 && !finishedRef.current && !winner) {
        finishedRef.current = true
        // 1s slop so a fire that lands right at deadline still has
        // a chance to resolve via minigame/fire before we force.
        window.setTimeout(() => {
          void api.sp.minigameFinish(sessionCode).catch(() => {})
        }, 1000)
      }
    }
    tick()
    const id = window.setInterval(tick, 50)
    return () => window.clearInterval(id)
  }, [mg, sessionCode, winner])

  if (!mg) {
    return (
      <main className="flex h-full w-full items-center justify-center">
        <p className="font-body text-2xl text-text/60">Loading minigame…</p>
      </main>
    )
  }

  return (
    <main className="relative flex h-full w-full flex-col items-center justify-center gap-8 overflow-hidden px-12 py-12">
      {/* Tense color palette for the minigame phase — orange + magenta
          glow, more energetic than the calm pick/lobby blues. */}
      <AmbientBackground
        glowA="rgba(249,115,22,0.20)"
        glowB="rgba(236,72,153,0.18)"
      />
      <div className="relative z-10 flex flex-col items-center gap-2">
        <span className="font-body text-base font-medium uppercase tracking-widest text-text/50">
          {mg.flavor === 'BULLSEYE' ? 'Bullseye' : 'Shot Clock'} · Minigame
        </span>
        <motion.h1
          initial={{ scale: 0.7, opacity: 0 }}
          animate={{
            scale: winner ? 1 : [1, 1.04, 1],
            opacity: 1,
          }}
          transition={{
            scale: winner
              ? { duration: 0.45, ease: [0.34, 1.56, 0.64, 1] }
              : { duration: 1.2, repeat: Infinity, ease: 'easeInOut' },
            opacity: { duration: 0.45 },
          }}
          className="font-display text-[clamp(2.5rem,6vw,5rem)] leading-none text-accent"
          style={{
            textShadow:
              '0 0 30px rgba(236,72,153,0.45), 0 0 70px rgba(236,72,153,0.18)',
          }}
        >
          {winner
            ? 'RESULTS'
            : mg.flavor === 'BULLSEYE'
            ? `AIM AT ${mg.target_quadrant}`
            : 'TAP IN THE GREEN'}
        </motion.h1>
        {!winner && (
          <motion.span
            className="font-mono text-3xl text-primary"
            // Pulse the timer in the final 3s as the room gets nervous.
            animate={{
              color: remainingMs < 3000 ? '#ef4444' : '#3b82f6',
              scale: remainingMs < 3000 ? [1, 1.12, 1] : 1,
            }}
            transition={{
              color: { duration: 0.2 },
              scale: remainingMs < 3000
                ? { duration: 0.55, repeat: Infinity, ease: 'easeInOut' }
                : { duration: 0.2 },
            }}
          >
            {(remainingMs / 1000).toFixed(1)}s
          </motion.span>
        )}
      </div>

      <div className="relative z-10">
        {mg.flavor === 'BULLSEYE' && !winner && (
          <BullseyeBoard
            target={mg.target_quadrant ?? 'A'}
            fires={fires}
            aims={aims}
          />
        )}
        {mg.flavor === 'SHOT_CLOCK' && !winner && (
          <ShotClockBar
            startedAtMs={mg.started_at * 1000}
            cycleMs={mg.cycle_ms ?? 3000}
            greenFrac={mg.green_frac ?? 0.3}
            fires={fires}
          />
        )}

        {winner && <WinnerPanel winner={winner} />}
      </div>
    </main>
  )
}

function BullseyeBoard({
  target,
  fires,
  aims,
}: {
  target: 'A' | 'B' | 'C' | 'D'
  fires: MinigameFireEvent[]
  aims: Record<number, 'A' | 'B' | 'C' | 'D'>
}) {
  const quads: Array<{ key: 'A' | 'B' | 'C' | 'D'; label: string }> = [
    { key: 'A', label: '▲ A' },
    { key: 'B', label: '▶ B' },
    { key: 'C', label: '▼ C' },
    { key: 'D', label: '◀ D' },
  ]
  return (
    <div className="grid grid-cols-2 gap-4 w-[clamp(20rem,40vw,32rem)]">
      {quads.map((q) => {
        const isTarget = q.key === target
        const firesHere = fires.filter((f) => f.quadrant === q.key)
        // Slice F — per-puck live aim reticles.
        const aimedBy = Object.entries(aims)
          .filter(([, quadrant]) => quadrant === q.key)
          .map(([pid]) => Number(pid))
        return (
          <motion.div
            key={q.key}
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{
              // Target quadrant pulses; non-targets stay still.
              scale: isTarget ? [1, 1.06, 1] : 1,
              opacity: 1,
            }}
            transition={
              isTarget
                ? { scale: { duration: 1.4, repeat: Infinity, ease: 'easeInOut' } }
                : { duration: 0.35 }
            }
            className={`relative flex aspect-square flex-col items-center justify-center rounded-3xl border-4 ${
              isTarget ? 'border-correct bg-correct/15' : 'border-text/15 bg-text/5'
            }`}
            style={{
              // Inner gradient on every card; only the target gets the
              // golden glow.
              backgroundImage:
                'linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0) 60%)',
              boxShadow: isTarget
                ? '0 0 60px rgba(251,191,36,0.55), 0 0 12px rgba(251,191,36,0.4) inset'
                : '0 4px 16px rgba(0,0,0,0.25)',
            }}
          >
            {/* Live aim reticles — faint per-puck halos */}
            <div className="absolute inset-2 flex flex-wrap items-start justify-end gap-1">
              <AnimatePresence>
                {aimedBy.map((pid) => (
                  <motion.span
                    key={`aim-${pid}`}
                    initial={{ scale: 0.4, opacity: 0 }}
                    animate={{ scale: 1, opacity: 0.85 }}
                    exit={{ scale: 0.4, opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    className="inline-block h-4 w-4 rounded-full ring-2 ring-bg"
                    style={{ backgroundColor: PUCK_COLOR[pid] ?? '#F8FAFC' }}
                    title={`Puck ${pid} aiming here`}
                  />
                ))}
              </AnimatePresence>
            </div>
            <span
              className={`font-display text-[clamp(2.5rem,5vw,4.5rem)] ${
                isTarget ? 'text-correct' : 'text-text/60'
              }`}
            >
              {q.label}
            </span>
            <div className="mt-2 flex flex-wrap gap-1">
              {firesHere.map((f, i) => (
                <span
                  key={`${f.puck_id}-${i}`}
                  className="rounded-full bg-primary/70 px-2 py-0.5 font-mono text-xs text-bg"
                >
                  P{f.puck_id} +{f.points}
                </span>
              ))}
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}

function ShotClockBar({
  startedAtMs,
  cycleMs,
  greenFrac,
  fires,
}: {
  startedAtMs: number
  cycleMs: number
  greenFrac: number
  fires: MinigameFireEvent[]
}) {
  const [pos, setPos] = useState(0) // 0..1
  // Guard a degenerate cycle so `% 0` can't yield NaN and freeze the sweep
  // pointer off-screen (audit tv-speed-pyramid-web).
  const safeCycleMs = cycleMs > 0 ? cycleMs : 3000
  useEffect(() => {
    let raf = 0
    const tick = () => {
      const elapsed = Date.now() - startedAtMs
      const p = (elapsed % safeCycleMs) / safeCycleMs
      setPos(p)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [startedAtMs, safeCycleMs])

  // Clamp so a bad green fraction can't render the zone off the track —
  // players tap relative to where it's drawn.
  const safeGreenFrac = clamp(greenFrac, 0, 1)
  const half = safeGreenFrac / 2
  const greenStart = 0.5 - half
  return (
    <div className="relative h-24 w-[clamp(28rem,60vw,56rem)] overflow-hidden rounded-full bg-text/10">
      {/* Green zone */}
      <div
        className="absolute inset-y-0 bg-correct/40"
        style={{
          left: `${greenStart * 100}%`,
          width: `${safeGreenFrac * 100}%`,
        }}
      />
      {/* Sweep pointer */}
      <motion.div
        className="absolute inset-y-0 w-2 bg-primary"
        animate={{ left: `${pos * 100}%` }}
        transition={{ duration: 0.05 }}
      />
      {/* Fire markers */}
      <div className="absolute inset-x-0 -bottom-10 flex justify-center gap-2 font-mono text-xs">
        {fires.map((f, i) => (
          <span
            key={`${f.puck_id}-${i}`}
            className="rounded-full bg-primary/70 px-2 py-0.5 text-bg"
          >
            P{f.puck_id} +{f.points}
          </span>
        ))}
      </div>
    </div>
  )
}

function WinnerPanel({ winner }: { winner: MinigameWinnerEvent }) {
  return (
    <div className="flex w-full max-w-4xl flex-col gap-3">
      <AnimatePresence>
        {winner.results.map((r, i) => (
          <motion.div
            key={r.puck_id}
            layout
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.4, delay: i * 0.1 }}
            className={`flex items-center justify-between rounded-2xl border-2 ${
              r.bonus === 500
                ? 'border-correct'
                : r.bonus === 200
                ? 'border-primary'
                : 'border-text/10'
            } bg-text/5 px-6 py-4`}
            style={
              r.bonus === 500
                ? { boxShadow: '0 0 40px rgba(251,191,36,0.35)' }
                : undefined
            }
          >
            <div className="flex items-center gap-4">
              <span className="font-display text-3xl text-text">
                Puck {r.puck_id}
              </span>
              <span className="font-body text-base text-text/60">
                {r.bonus === 500
                  ? '🥇 +500'
                  : r.bonus === 200
                  ? '🥈 +200'
                  : 'no bonus'}
              </span>
            </div>
            <span className="font-mono text-2xl text-text">
              {r.cumulative_total.toLocaleString()}
            </span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
