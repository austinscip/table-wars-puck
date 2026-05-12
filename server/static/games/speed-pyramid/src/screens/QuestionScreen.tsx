import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { getSocket } from '../lib/socket'
import { api, type SpeedPyramidQuestion } from '../lib/api'
import { audio } from '../lib/audio'
import AnswerPill from '../components/AnswerPill'
import TimerBar from '../components/TimerBar'

type Phase = 'awaiting_question' | 'answering' | 'reveal'

interface QuestionShowEvent {
  session_code: string
  question: SpeedPyramidQuestion
  round: number
  total_rounds: number
  started_at: number
  expected_pucks: number[]
}

interface AnswerLockedEvent {
  session_code: string
  puck_id: number
  answer: 'A' | 'B' | 'C' | 'D'
  question_id: number
  color: string
}

interface AnswerPreviewEvent {
  session_code: string
  puck_id: number
  answer: 'A' | 'B' | 'C' | 'D' | null
}

interface RevealResult {
  puck_id: number
  answer: 'A' | 'B' | 'C' | 'D' | null
  is_correct: boolean
  points: number
  tier: string
  response_time_ms: number | null
  color: string
  color_name: string
  cumulative_total: number
}

interface RevealEvent {
  session_code: string
  question_id: number
  correct_answer: 'A' | 'B' | 'C' | 'D'
  results: RevealResult[]
}

const REVEAL_HOLD_MS = 2500

interface PlayerLane {
  puck_id: number
  color: string
  preview: 'A' | 'B' | 'C' | 'D' | null
  locked: 'A' | 'B' | 'C' | 'D' | null
  reveal: RevealResult | null
  cumulative: number
}

function tierColorClass(tier: string | null): string {
  switch (tier) {
    case 'LEGENDARY': return 'text-correct'
    case 'EXPERT':    return 'text-primary'
    case 'AVERAGE':   return 'text-accent'
    case 'TIMEOUT':
    case 'WRONG':     return 'text-wrong'
    default:          return 'text-text/60'
  }
}

export default function QuestionScreen() {
  const navigate = useNavigate()
  const { sessionCode } = useParams<{ sessionCode: string }>()
  const [params] = useSearchParams()
  const isDemo = params.get('demo') === '1'
  const demoPuckId = Number(params.get('puck_id') ?? '99')

  const [question, setQuestion] = useState<SpeedPyramidQuestion | null>(null)
  const [round, setRound] = useState(0)
  const [totalRounds, setTotalRounds] = useState(7)
  const [startedAt, setStartedAt] = useState(0)
  const [phase, setPhase] = useState<Phase>('awaiting_question')
  const [reveal, setReveal] = useState<RevealEvent | null>(null)
  const [lanes, setLanes] = useState<Record<number, PlayerLane>>({})

  const lastTickRef = useRef(-1)
  const demoAnsweredRef = useRef<Set<number>>(new Set())
  const forceRevealTimerRef = useRef<number | null>(null)
  const advanceTimerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!sessionCode) return
    const socket = getSocket()
    socket.emit('join_session_room', { session_code: sessionCode })

    function onQuestionShow(p: QuestionShowEvent) {
      if (p.session_code !== sessionCode) return
      setQuestion(p.question)
      setRound(p.round)
      setTotalRounds(p.total_rounds)
      setStartedAt(p.started_at)
      setPhase('answering')
      setReveal(null)
      lastTickRef.current = -1
      audio.questionShow()

      // Initialize lanes — one per expected puck. Preserve cumulative
      // totals across rounds.
      setLanes((prev) => {
        const next: Record<number, PlayerLane> = {}
        for (const pid of p.expected_pucks) {
          next[pid] = {
            puck_id: pid,
            color: prev[pid]?.color ?? '#F8FAFC',
            preview: null,
            locked: null,
            reveal: null,
            cumulative: prev[pid]?.cumulative ?? 0,
          }
        }
        return next
      })

      // Schedule a force-reveal call slightly after the timer's
      // nominal expiry. The server's _maybe_emit_reveal is idempotent
      // — if all pucks have already answered, it does nothing.
      if (forceRevealTimerRef.current) window.clearTimeout(forceRevealTimerRef.current)
      const elapsedMs = Math.max(0, Date.now() - p.started_at * 1000)
      const remainingMs = Math.max(500, p.question.time_limit * 1000 - elapsedMs + 800)
      forceRevealTimerRef.current = window.setTimeout(() => {
        forceRevealTimerRef.current = null
        void api.sp.forceReveal(sessionCode).catch(() => {})
      }, remainingMs)

      // Demo-mode auto-answer (single-puck demo flow).
      if (isDemo && !demoAnsweredRef.current.has(p.question.id)) {
        demoAnsweredRef.current.add(p.question.id)
        const letters = ['A', 'B', 'C', 'D'] as const
        window.setTimeout(() => {
          const a = letters[Math.floor(Math.random() * 4)]
          const elapsed = Math.max(0, Date.now() - p.started_at * 1000)
          void api.sp.answer(sessionCode, demoPuckId, p.question.id, a, Math.round(elapsed))
        }, 1200 + Math.random() * 1800)
      }
    }

    function onAnswerLocked(p: AnswerLockedEvent) {
      if (p.session_code !== sessionCode) return
      setLanes((prev) => {
        const lane = prev[p.puck_id] ?? {
          puck_id: p.puck_id,
          color: p.color,
          preview: null,
          locked: null,
          reveal: null,
          cumulative: 0,
        }
        return {
          ...prev,
          [p.puck_id]: { ...lane, locked: p.answer, color: p.color, preview: null },
        }
      })
      audio.lockIn()
    }

    function onAnswerPreview(p: AnswerPreviewEvent) {
      if (p.session_code !== sessionCode) return
      setLanes((prev) => {
        const lane = prev[p.puck_id]
        if (!lane) return prev
        return { ...prev, [p.puck_id]: { ...lane, preview: p.answer } }
      })
    }

    function onReveal(p: RevealEvent) {
      if (p.session_code !== sessionCode) return
      if (forceRevealTimerRef.current) {
        window.clearTimeout(forceRevealTimerRef.current)
        forceRevealTimerRef.current = null
      }
      setReveal(p)
      setPhase('reveal')
      setLanes((prev) => {
        const next = { ...prev }
        for (const r of p.results) {
          next[r.puck_id] = {
            puck_id: r.puck_id,
            color: r.color,
            preview: null,
            locked: r.answer,
            reveal: r,
            cumulative: r.cumulative_total,
          }
        }
        return next
      })
      audio.reveal()
      const anyCorrect = p.results.some((r) => r.is_correct)
      window.setTimeout(() => {
        if (anyCorrect) audio.correct()
        else audio.wrong()
      }, 120)
      // Auto-advance after the hold.
      if (advanceTimerRef.current) window.clearTimeout(advanceTimerRef.current)
      advanceTimerRef.current = window.setTimeout(() => {
        api.sp.loadQuestion(sessionCode).catch(() => navigate(`/scoreboard/${sessionCode}`))
      }, REVEAL_HOLD_MS)
    }

    function onMatchEnded() {
      navigate(`/scoreboard/${sessionCode}`)
    }

    socket.on('question_show', onQuestionShow)
    socket.on('answer_locked', onAnswerLocked)
    socket.on('answer_preview', onAnswerPreview)
    socket.on('reveal', onReveal)
    socket.on('match_ended', onMatchEnded)

    api.sp.loadQuestion(sessionCode).catch(() => {})

    return () => {
      socket.off('question_show', onQuestionShow)
      socket.off('answer_locked', onAnswerLocked)
      socket.off('answer_preview', onAnswerPreview)
      socket.off('reveal', onReveal)
      socket.off('match_ended', onMatchEnded)
      if (forceRevealTimerRef.current) {
        window.clearTimeout(forceRevealTimerRef.current)
        forceRevealTimerRef.current = null
      }
      if (advanceTimerRef.current) {
        window.clearTimeout(advanceTimerRef.current)
        advanceTimerRef.current = null
      }
    }
  }, [sessionCode, navigate, isDemo, demoPuckId])

  // Countdown ticks in the last 3 seconds.
  useEffect(() => {
    if (phase !== 'answering' || !question) return
    const id = window.setInterval(() => {
      const elapsedMs = Date.now() - startedAt * 1000
      const remainingSec = Math.max(0, Math.ceil((question.time_limit * 1000 - elapsedMs) / 1000))
      if (remainingSec <= 3 && remainingSec > 0 && remainingSec !== lastTickRef.current) {
        lastTickRef.current = remainingSec
        if (remainingSec === 1) audio.tickFinal()
        else audio.tick()
      }
    }, 100)
    return () => window.clearInterval(id)
  }, [phase, question, startedAt])

  if (!question) {
    return (
      <main className="flex h-full w-full items-center justify-center">
        <p className="font-body text-2xl text-text/60">Loading question…</p>
      </main>
    )
  }

  const pillState = (letter: 'A' | 'B' | 'C' | 'D') => {
    if (phase === 'reveal' && reveal) {
      if (letter === reveal.correct_answer) return 'correct' as const
      // If any player picked this and was wrong, mark it 'wrong'; else dim.
      const someoneWrongOnThis = reveal.results.some(
        (r) => r.answer === letter && !r.is_correct,
      )
      if (someoneWrongOnThis) return 'wrong' as const
      return 'dim' as const
    }
    // In answering phase, an 'idle' pill — no preview overlay because
    // previews are now shown in the sidebar per-player.
    return 'idle' as const
  }

  const laneList = Object.values(lanes).sort((a, b) => a.puck_id - b.puck_id)

  return (
    <main className="relative flex h-full w-full flex-row gap-8 px-8 py-8">
      {/* Main column */}
      <section className="flex flex-1 flex-col gap-6">
        <header className="flex items-center justify-between">
          <span className="font-display text-3xl tracking-wide text-text/70">
            {question.category}
          </span>
          <div className="flex items-center gap-3">
            {Array.from({ length: totalRounds }).map((_, i) => {
              const done = i + 1 < round
              const active = i + 1 === round
              return (
                <span
                  key={i}
                  className={`h-3 w-3 rounded-full transition-colors duration-300 ${
                    done ? 'bg-correct' : active ? 'bg-primary' : 'bg-text/15'
                  } ${active ? 'ring-2 ring-primary/40 ring-offset-2 ring-offset-bg' : ''}`}
                />
              )
            })}
          </div>
        </header>

        <TimerBar
          durationSec={question.time_limit}
          startedAt={startedAt}
          frozen={phase === 'reveal'}
        />

        <motion.div
          key={question.id}
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.45, ease: [0.34, 1.56, 0.64, 1] }}
          className="flex flex-col gap-3"
        >
          {question.setup ? (
            <p className="font-body text-[clamp(1.25rem,2.4vw,2.25rem)] leading-snug text-text/80">
              {question.setup}
            </p>
          ) : null}
          <h1 className="font-display text-[clamp(2rem,4.5vw,4.5rem)] leading-tight tracking-tight text-text">
            {question.question}
          </h1>
        </motion.div>

        <div className="grid flex-1 grid-cols-1 gap-4 md:grid-cols-2">
          {(['A', 'B', 'C', 'D'] as const).map((letter, i) => (
            <AnswerPill
              key={letter}
              letter={letter}
              text={question.answers[letter]}
              state={pillState(letter)}
              index={i}
            />
          ))}
        </div>

        <AnimatePresence>
          {phase === 'reveal' && reveal && !reveal.results.some((r) => r.is_correct) ? (
            <motion.p
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.3 }}
              className="font-body text-xl text-text/80"
            >
              Correct answer:{' '}
              <span className="font-display text-2xl text-correct">
                {reveal.correct_answer} · {question.answers[reveal.correct_answer]}
              </span>
            </motion.p>
          ) : null}
        </AnimatePresence>
      </section>

      {/* Sidebar */}
      <aside className="flex w-[clamp(14rem,22vw,22rem)] flex-col gap-3">
        <span className="font-body text-base font-medium uppercase tracking-widest text-text/40">
          Players
        </span>
        <AnimatePresence>
          {laneList.map((lane) => {
            const r = lane.reveal
            const stateLabel =
              r
                ? `${r.tier}${r.points ? ` +${r.points}` : ''}`
                : lane.locked
                ? `LOCKED · ${lane.locked}`
                : lane.preview
                ? `aim · ${lane.preview}`
                : 'thinking…'
            const stateColorClass = r ? tierColorClass(r.tier) : 'text-text/60'
            const isWinningLane = phase === 'reveal' && r && r.is_correct
            return (
              <motion.div
                key={lane.puck_id}
                layout
                initial={{ y: 10, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -10, opacity: 0 }}
                transition={{ duration: 0.25 }}
                className={`flex items-center gap-3 rounded-2xl border-2 ${
                  isWinningLane ? 'border-correct' : 'border-text/10'
                } bg-text/5 px-4 py-3`}
                style={isWinningLane ? { boxShadow: '0 0 30px rgba(251,191,36,0.4)' } : undefined}
              >
                <div
                  className="flex h-12 w-12 flex-none items-center justify-center rounded-full font-display text-2xl"
                  style={{ backgroundColor: lane.color, color: '#0A0E1A' }}
                >
                  {lane.puck_id}
                </div>
                <div className="flex flex-1 flex-col">
                  <span className="font-body text-base font-bold text-text">
                    Puck {lane.puck_id}
                  </span>
                  <span className={`font-body text-sm ${stateColorClass}`}>
                    {stateLabel}
                  </span>
                </div>
                <div className="flex-none text-right">
                  <span className="font-mono text-xl font-bold text-text">
                    {lane.cumulative.toLocaleString()}
                  </span>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
        {laneList.length === 0 ? (
          <p className="font-body text-base text-text/50">No players yet…</p>
        ) : null}
      </aside>
    </main>
  )
}
