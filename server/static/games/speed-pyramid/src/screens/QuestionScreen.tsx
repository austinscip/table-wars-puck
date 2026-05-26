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
  audio_url?: string | null
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
  commentary_correct?: string
  commentary_wrong?: string
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
    const sc = sessionCode  // narrow once for inner closures
    const socket = getSocket()
    socket.emit('join_session_room', { session_code: sc })
    // Defensive: re-join the room on every (re)connect so a flapping
    // socket doesn't drop us out of the broadcast room and miss the
    // reveal / question_show events that drive the match forward.
    function onConnect() {
      socket.emit('join_session_room', { session_code: sc })
    }
    socket.on('connect', onConnect)

    // Single place that schedules the next-question advance. Called by
    // both the reveal socket event AND the force-reveal POST response,
    // so a missed socket event can't strand the match. Replaces any
    // pending advance timer so we never queue two.
    function scheduleAdvanceToNextQuestion() {
      if (advanceTimerRef.current) window.clearTimeout(advanceTimerRef.current)
      advanceTimerRef.current = window.setTimeout(() => {
        advanceTimerRef.current = null
        api.sp
          .loadQuestion(sc)
          .then((resp) => {
            applyQuestionShown({
              question: resp.question,
              audio_url: resp.audio_url,
              round: resp.round,
              total_rounds: resp.total_rounds,
              started_at: resp.started_at,
              expected_pucks: resp.expected_pucks,
            })
          })
          .catch(() => navigate(`/scoreboard/${sc}`))
      }, REVEAL_HOLD_MS)
    }

    // Single code path for "we have a new question to show" — fired by
    // either the question_show socket event (primary) or the
    // load-question REST response (fallback when the socket missed it).
    // Idempotent: re-applying the same question_id is a no-op for the
    // visible state and replaces any prior force-reveal timer.
    function applyQuestionShown(args: {
      question: SpeedPyramidQuestion
      audio_url?: string | null
      round: number
      total_rounds: number
      started_at: number
      expected_pucks?: number[]
    }) {
      setQuestion((cur) => {
        if (cur && cur.id === args.question.id) return cur
        return args.question
      })
      setRound(args.round)
      setTotalRounds(args.total_rounds)
      setReveal(null)
      lastTickRef.current = -1
      audio.questionShow()

      // Begin-answering routine — flips phase, syncs startedAt to the
      // server's authoritative start moment, and schedules the
      // force-reveal fallback. Hoisted so the narration handoff can
      // call it after the MP3 ends instead of running the countdown
      // concurrent with the narration.
      const beginAnswering = (at: number) => {
        setStartedAt(at)
        setPhase('answering')
        if (forceRevealTimerRef.current) {
          window.clearTimeout(forceRevealTimerRef.current)
        }
        const elapsedMs = Math.max(0, Date.now() - at * 1000)
        const remainingMs = Math.max(
          500,
          args.question.time_limit * 1000 - elapsedMs + 800,
        )
        forceRevealTimerRef.current = window.setTimeout(() => {
          forceRevealTimerRef.current = null
          api.sp.forceReveal(sc)
            .then(() => {
              // Belt-and-suspenders: schedule the advance ourselves
              // even if the socket `reveal` event is missed.
              scheduleAdvanceToNextQuestion()
            })
            .catch(() => {})
        }, remainingMs)
      }

      if (args.audio_url) {
        // Narration plays first. Until it ends, the TimerBar is frozen
        // (phase !== 'answering') and the force-reveal timer is not
        // armed. The countdown should reflect "I have 15s starting
        // when the host stops reading", not "I have 15s starting at
        // the moment the question card slid in".
        setPhase('awaiting_question')
        // Set startedAt to roughly now so the (frozen) bar renders at
        // 100% during narration instead of pre-depleted.
        setStartedAt(Date.now() / 1000)
        const a = new Audio(args.audio_url)
        a.preload = 'auto'
        let started = false
        const handoff = () => {
          if (started) return
          started = true
          api.sp
            .startTimer(sc)
            .then((resp) => beginAnswering(resp.started_at))
            .catch(() => beginAnswering(Date.now() / 1000))
        }
        a.addEventListener('ended', handoff)
        a.addEventListener('error', handoff)
        // Belt-and-suspenders: even if 'ended' never fires, start the
        // timer after the audio's full duration (or a 1s ceiling for
        // missing files where duration is NaN).
        void a.play().catch(handoff)
        window.setTimeout(
          handoff,
          1000 + (a.duration > 0 ? a.duration * 1000 : 0),
        )
      } else {
        // No narration — start countdown immediately, using the
        // server's args.started_at so the TV stays synced with the
        // server-side force-reveal timer.
        beginAnswering(args.started_at)
        void api.sp.startTimer(sc).catch(() => {})
      }

      if (args.expected_pucks && args.expected_pucks.length) {
        setLanes((prev) => {
          const next: Record<number, PlayerLane> = {}
          for (const pid of args.expected_pucks!) {
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
      } else {
        // No expected_pucks in this payload — just reset per-lane round
        // state, preserve color + cumulative.
        setLanes((prev) => {
          const next: Record<number, PlayerLane> = {}
          for (const pid of Object.keys(prev).map(Number)) {
            next[pid] = { ...prev[pid], preview: null, locked: null, reveal: null }
          }
          return next
        })
      }

      if (isDemo && !demoAnsweredRef.current.has(args.question.id)) {
        demoAnsweredRef.current.add(args.question.id)
        const letters = ['A', 'B', 'C', 'D'] as const
        window.setTimeout(() => {
          const a = letters[Math.floor(Math.random() * 4)]
          const elapsed = Math.max(0, Date.now() - args.started_at * 1000)
          void api.sp.answer(sc, demoPuckId, args.question.id, a, Math.round(elapsed))
        }, 1200 + Math.random() * 1800)
      }
    }

    function onQuestionShow(p: QuestionShowEvent) {
      if (p.session_code !== sessionCode) return
      applyQuestionShown({
        question: p.question,
        audio_url: p.audio_url,
        round: p.round,
        total_rounds: p.total_rounds,
        started_at: p.started_at,
        expected_pucks: p.expected_pucks,
      })
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
      // Hybrid reveal audio: only the unanimous-correct or unanimous-
      // wrong cases get the chord (audio.correct / audio.wrong). Mixed
      // outcomes play the neutral reveal stinger only — playing
      // audio.correct() when some pucks lost (or audio.wrong() when
      // some pucks won) reads as "the room won/lost" and steps on the
      // per-puck reveal lanes. The 140ms stinger inside the unanimous
      // paths used to overlap the chord 120ms later — drop it there
      // and keep it only as the mixed-case neutral beat.
      const allCorrect =
        p.results.length > 0 && p.results.every((r) => r.is_correct)
      const allWrong =
        p.results.length > 0 && p.results.every((r) => !r.is_correct)
      if (allCorrect) {
        audio.correct()
      } else if (allWrong) {
        audio.wrong()
      } else {
        audio.reveal()
      }
      scheduleAdvanceToNextQuestion()
    }

    function onMatchEnded() {
      navigate(`/scoreboard/${sessionCode}`)
    }

    function onLobbyCancelled() {
      // Admin reset / Back to start mid-match: bounce to title.
      navigate('/', { replace: true })
    }

    socket.on('question_show', onQuestionShow)
    socket.on('answer_locked', onAnswerLocked)
    socket.on('answer_preview', onAnswerPreview)
    socket.on('reveal', onReveal)
    socket.on('match_ended', onMatchEnded)
    socket.on('lobby_cancelled', onLobbyCancelled)

    // Initial load — also apply the response inline so the very first
    // question never depends on the socket event arriving in time.
    api.sp
      .loadQuestion(sessionCode)
      .then((resp) => {
        applyQuestionShown({
          question: resp.question,
          audio_url: resp.audio_url,
          round: resp.round,
          total_rounds: resp.total_rounds,
          started_at: resp.started_at,
          expected_pucks: resp.expected_pucks,
        })
      })
      .catch(() => {})

    return () => {
      socket.off('connect', onConnect)
      socket.off('question_show', onQuestionShow)
      socket.off('answer_locked', onAnswerLocked)
      socket.off('answer_preview', onAnswerPreview)
      socket.off('reveal', onReveal)
      socket.off('match_ended', onMatchEnded)
      socket.off('lobby_cancelled', onLobbyCancelled)
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
          frozen={phase !== 'answering'}
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

        {/* Host commentary on reveal. Show the correct-tier line if any
            puck got it right, the wrong-tier line if any puck got it
            wrong. Both render when answers were mixed. */}
        <AnimatePresence>
          {phase === 'reveal' && reveal ? (
            <motion.div
              initial={{ y: 16, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.35, delay: 0.45 }}
              className="flex flex-col gap-2 font-body text-lg italic text-text/85"
            >
              {reveal.commentary_correct &&
              reveal.results.some((r) => r.is_correct) ? (
                <span data-testid="commentary-correct" className="text-correct">
                  {reveal.commentary_correct}
                </span>
              ) : null}
              {reveal.commentary_wrong &&
              reveal.results.some((r) => !r.is_correct) ? (
                <span data-testid="commentary-wrong" className="text-wrong">
                  {reveal.commentary_wrong}
                </span>
              ) : null}
            </motion.div>
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
