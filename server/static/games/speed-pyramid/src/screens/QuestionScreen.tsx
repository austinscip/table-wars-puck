import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { getSocket } from '../lib/socket'
import { api, type SpeedPyramidQuestion } from '../lib/api'
import { audio } from '../lib/audio'
import AnswerPill from '../components/AnswerPill'
import TimerBar from '../components/TimerBar'
import OnboardingOverlay from '../components/OnboardingOverlay'

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
  // Track the currently-playing narration so a second applyQuestionShown
  // for the same question (REST + socket race) doesn't stack two
  // overlapping Audio elements that play in echo.
  const narrationAudioRef = useRef<HTMLAudioElement | null>(null)
  const narratedQidRef = useRef<number | null>(null)
  // R022b: pending narration timers (the 600ms delayed play + the
  // metadata-duration fallback). These MUST be cleared on unmount/reveal,
  // otherwise a delayed play() can fire AFTER the screen navigated away
  // and the host voice bleeds into the next screen.
  const narrationTimersRef = useRef<number[]>([])
  // Slice G — ROUND N intro. Show for fixed ~1.6s then unmount, never
  // depend on phase changing to hide it (the phase 'awaiting_question'
  // could stick if narration audio errors before handoff fires).
  const [showRoundIntro, setShowRoundIntro] = useState(false)

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
            // Slice E1/E2: server may return a category-pick or
            // minigame phase instead of a question. Hand off to the
            // dedicated screen; it'll navigate back here once the
            // phase resolves.
            if (resp.phase === 'category_pick') {
              navigate(`/category-pick/${sc}`, { replace: true })
              return
            }
            if (resp.phase === 'minigame') {
              navigate(`/minigame/${sc}`, { replace: true })
              return
            }
            if (!resp.question) return
            applyQuestionShown({
              question: resp.question,
              audio_url: resp.audio_url,
              round: resp.round,
              total_rounds: resp.total_rounds,
              started_at: resp.started_at ?? Date.now() / 1000,
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
        // R022 fix: do NOT override phase if reveal already arrived.
        // The narration handoff can fire AFTER both pucks have
        // already answered (when narration is long or when REST
        // shortcuts answer-post). Without this guard, beginAnswering
        // sets phase='answering' over the existing phase='reveal',
        // which makes the commentary motion.div unmount via
        // AnimatePresence. Symptom: commentary text appears for ~500ms
        // and then vanishes.
        setPhase((cur) => (cur === 'reveal' ? cur : 'answering'))
        setStartedAt(at)
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
          // R036 fix: schedule the advance whether force-reveal
          // succeeds OR fails. The server returns HTTP 400 (postJson
          // throws) when current_question_id is None — exactly the
          // stranded-round case a peer Play-Again/reset/restart causes,
          // which is precisely when the fallback must rescue the TV. The
          // old empty .catch swallowed that 400 and left the TV parked on
          // the revealed question forever. Use .finally so the advance is
          // armed in both branches.
          api.sp.forceReveal(sc)
            .catch(() => {})
            .finally(() => {
              // Belt-and-suspenders: schedule the advance ourselves
              // even if the socket `reveal` event is missed or the
              // force-reveal call failed (e.g. no current question).
              scheduleAdvanceToNextQuestion()
            })
        }, remainingMs)
      }

      if (args.audio_url) {
        // Narration plays first. Until it ends, the TimerBar is frozen
        // (phase !== 'answering') and the force-reveal timer is not
        // armed. The countdown should reflect "I have 15s starting
        // when the host stops reading", not "I have 15s starting at
        // the moment the question card slid in".

        // Guard against double-narration: applyQuestionShown can fire
        // twice for the same question (initial REST loadQuestion + the
        // question_show socket event a beat later). Without this gate
        // two Audio elements get created and play() in parallel, which
        // sounds exactly like an echo.
        if (narratedQidRef.current === args.question.id) {
          // Already narrated this question — fall through to the rest of
          // applyQuestionShown without starting another playback.
        } else {
          narratedQidRef.current = args.question.id
          // Kill any narration still in flight from a previous question.
          // R022b: clear pending delayed-play timers too.
          narrationTimersRef.current.forEach((id) => window.clearTimeout(id))
          narrationTimersRef.current = []
          // Show ROUND N intro for ~1.6s on every new question.
          // Pushed AFTER the timer-ref reset above so it isn't
          // immediately cancelled. Self-contained timeout — does
          // NOT go into narrationTimersRef so the next question's
          // narration-clear can't kill it mid-animation.
          setShowRoundIntro(true)
          window.setTimeout(() => setShowRoundIntro(false), 1600)
          if (narrationAudioRef.current) {
            try {
              narrationAudioRef.current.pause()
              narrationAudioRef.current.src = ''
            } catch {
              /* swallow — element may already be torn down */
            }
            narrationAudioRef.current = null
          }
        setPhase('awaiting_question')
        // Set startedAt to roughly now so the (frozen) bar renders at
        // 100% during narration instead of pre-depleted.
        setStartedAt(Date.now() / 1000)
        const a = new Audio(args.audio_url)
        a.preload = 'auto'
        narrationAudioRef.current = a
        let started = false
        let metadataTimer: number | null = null
        // R023: small gap between narration end and countdown start so
        // the user gets a "breath" before they need to answer.
        const HANDOFF_BREATH_MS = 800
        const handoff = () => {
          if (started) return
          started = true
          if (metadataTimer !== null) window.clearTimeout(metadataTimer)
          // R048: track the breath timer in narrationTimersRef like the
          // metadata/play timers, otherwise the unmount/reveal cleanup
          // can't cancel it — an orphaned breath fires beginAnswering()
          // (POST /api/sp/start-timer) on a dead screen.
          const breathTimer = window.setTimeout(() => {
            api.sp
              .startTimer(sc)
              .then((resp) => beginAnswering(resp.started_at))
              .catch(() => beginAnswering(Date.now() / 1000))
          }, HANDOFF_BREATH_MS)
          narrationTimersRef.current.push(breathTimer)
        }
        a.addEventListener('ended', handoff)
        a.addEventListener('error', handoff)
        // Absolute safety net: if the MP3 stalls mid-load on flaky bar WiFi
        // (neither 'ended' nor 'error' nor 'loadedmetadata' ever fires), the
        // question would hang in 'awaiting_question' forever. Force the handoff
        // after a generous cap so the round always becomes answerable (audit
        // polish-2026-06-06).
        const STALL_GUARD_MS = 15000
        const stallTimer = window.setTimeout(handoff, STALL_GUARD_MS)
        narrationTimersRef.current.push(stallTimer)
        // 'loadedmetadata' fires once a.duration is known (typically
        // within tens of ms of starting to load). Only then can we
        // schedule a sane fallback timeout: duration + 1s grace. The
        // previous code referenced a.duration at construction time
        // when it's NaN, fell back to a fixed 1000 ms, and cut every
        // narration off at 1 second — countdown started early.
        a.addEventListener('loadedmetadata', () => {
          if (started) return
          const dur = isFinite(a.duration) && a.duration > 0 ? a.duration : 0
          if (dur > 0) {
            metadataTimer = window.setTimeout(handoff, dur * 1000 + 1000)
            narrationTimersRef.current.push(metadataTimer)
          }
        })
        // R021: delay narration playback by 600ms so the question card
        // finishes its 450ms framer-motion slide-in before the host
        // starts reading. Otherwise audio fires the moment React
        // commits the new card and feels like it leaked from the
        // previous transition.
        const PLAY_DELAY_MS = 600
        const playTimer = window.setTimeout(() => {
          if (started) return
          void a.play().catch(handoff)
        }, PLAY_DELAY_MS)
        narrationTimersRef.current.push(playTimer)
        // If the question rotates before we even started playing, kill
        // the delayed start so it doesn't bleed into the next phase.
        a.addEventListener('emptied', () => window.clearTimeout(playTimer))
        }  // end narration-not-yet-started branch
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
      // R022: if narration is still playing (both pucks answered
      // before the host finished reading the setup), kill it so it
      // doesn't bleed into the reveal audio. R022b: clear pending
      // delayed-play timers too.
      narrationTimersRef.current.forEach((id) => window.clearTimeout(id))
      narrationTimersRef.current = []
      if (narrationAudioRef.current) {
        try {
          narrationAudioRef.current.pause()
          narrationAudioRef.current.src = ''
        } catch {
          /* swallow */
        }
        narrationAudioRef.current = null
      }
      // Defensive: a malformed reveal lacking `results` would otherwise throw
      // here, and a throw inside this socket handler isn't caught by the
      // ErrorBoundary (it only catches render) — it would strand the TV on the
      // answering screen with the force-reveal timer already cleared. Default
      // to [] so the reveal still renders and the advance still schedules
      // (audit tv-speed-pyramid-web).
      const results = Array.isArray(p.results) ? p.results : []
      setReveal({ ...p, results })
      setPhase('reveal')
      setLanes((prev) => {
        const next = { ...prev }
        for (const r of results) {
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
        results.length > 0 && results.every((r) => r.is_correct)
      const allWrong =
        results.length > 0 && results.every((r) => !r.is_correct)
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
        // Slice E1/E2: if the very first load lands on a pick or
        // minigame phase, redirect to the dedicated screen.
        if (resp.phase === 'category_pick') {
          navigate(`/category-pick/${sessionCode}`, { replace: true })
          return
        }
        if (resp.phase === 'minigame') {
          navigate(`/minigame/${sessionCode}`, { replace: true })
          return
        }
        if (!resp.question) return
        applyQuestionShown({
          question: resp.question,
          audio_url: resp.audio_url,
          round: resp.round,
          total_rounds: resp.total_rounds,
          started_at: resp.started_at ?? Date.now() / 1000,
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
      // R022: stop narration on unmount so it doesn't bleed into the
      // next screen (lobby_cancelled, match_ended, navigate to
      // /category-pick or /minigame). R022b: also clear any pending
      // delayed-play timer so a play() can't fire after we've left.
      narrationTimersRef.current.forEach((id) => window.clearTimeout(id))
      narrationTimersRef.current = []
      if (narrationAudioRef.current) {
        try {
          narrationAudioRef.current.pause()
          narrationAudioRef.current.src = ''
        } catch {
          /* swallow */
        }
        narrationAudioRef.current = null
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
      {/* Track E — first-time 'how to play' card for a cold walk-up. Self-gates
          (shows once per browser via localStorage) and auto-fades, so it only
          ever appears on a TV's very first question. */}
      <OnboardingOverlay />
      {/* Slice G — ROUND N intro card. Fires once per round during
          host narration (phase='awaiting_question'), fades out before
          answering begins. AnimatePresence keyed on round so the
          spring re-fires per round. Non-blocking — pointer-events
          off + absolute layered above content. */}
      <AnimatePresence>
        {showRoundIntro && round > 0 ? (
          <motion.div
            key={`round-intro-${round}`}
            initial={{ scale: 0.4, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 1.5, opacity: 0 }}
            transition={{ duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }}
            className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center"
          >
            <span className="font-display text-[clamp(6rem,18vw,18rem)] leading-none tracking-tight text-primary drop-shadow-[0_0_60px_rgba(96,165,250,0.5)]">
              ROUND {round}
            </span>
          </motion.div>
        ) : null}
      </AnimatePresence>

      {/* Slice G — animated gradient backdrop that shifts per round.
          Pure CSS conic-gradient + Framer Motion opacity; no
          third-party assets. */}
      <motion.div
        key={`bg-${round}`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.2 }}
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background: `radial-gradient(ellipse at 15% 0%, rgba(96,165,250,0.55), transparent 55%),
                       radial-gradient(ellipse at 85% 100%, rgba(251,191,36,0.45), transparent 55%),
                       radial-gradient(circle at 50% 50%, rgba(168,85,247,0.30), transparent 70%)`,
        }}
      />

      {/* Main column */}
      <section className="flex flex-1 flex-col gap-6">
        <header className="flex items-center justify-between">
          <motion.span
            key={question.category}
            initial={{ x: -12, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
            className="font-display text-[clamp(1.5rem,3vw,3rem)] tracking-wide text-text/90"
          >
            {question.category}
          </motion.span>
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
          {(['A', 'B', 'C', 'D'] as const).map((letter, i) => {
            // Live "who's aiming here" — every lane currently previewing
            // (but not yet locked on) this letter contributes a colored
            // dot in the pill. Lets the bar see the room thinking.
            const previewBy = laneList
              .filter((l) => l.preview === letter && l.locked === null)
              .map((l) => ({ puck_id: l.puck_id, color: l.color }))
            return (
              <AnswerPill
                key={letter}
                letter={letter}
                text={question.answers[letter]}
                state={pillState(letter)}
                index={i}
                previewBy={previewBy}
              />
            )
          })}
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

        {/* Slice G — commentary overlay card. Replaces the previous
            italic-span block: semi-transparent panel, slides up on
            reveal, holds the eye on the host's line. Same data-testid
            anchors so e2e/audit gates keep working. */}
        <AnimatePresence>
          {phase === 'reveal' && reveal ? (
            <motion.div
              initial={{ y: 24, opacity: 0, scale: 0.96 }}
              animate={{ y: 0, opacity: 1, scale: 1 }}
              exit={{ y: -12, opacity: 0 }}
              transition={{
                duration: 0.45, delay: 0.45,
                ease: [0.34, 1.56, 0.64, 1],
              }}
              className="mt-4 flex w-full max-w-3xl flex-col gap-3 self-center rounded-2xl border border-text/10 bg-text/5 px-8 py-5 font-body text-2xl shadow-2xl backdrop-blur"
            >
              {reveal.commentary_correct &&
              reveal.results.some((r) => r.is_correct) ? (
                <span data-testid="commentary-correct" className="font-display text-correct">
                  {reveal.commentary_correct}
                </span>
              ) : null}
              {reveal.commentary_wrong &&
              reveal.results.some((r) => !r.is_correct) ? (
                <span data-testid="commentary-wrong" className="font-display text-wrong">
                  {reveal.commentary_wrong}
                </span>
              ) : null}
            </motion.div>
          ) : null}
        </AnimatePresence>
      </section>

      {/* Sidebar. At >4 players the single-column layout overflows
          720p TVs; switch to a 2-column grid + wider aside so all 8
          lanes fit. PUCK_COLORS server-side has 8 entries so the
          system was always half-designed for this scale. */}
      <aside
        className={
          laneList.length > 4
            ? 'flex w-[clamp(22rem,36vw,36rem)] flex-col gap-3'
            : 'flex w-[clamp(14rem,22vw,22rem)] flex-col gap-3'
        }
      >
        <span className="font-body text-base font-medium uppercase tracking-widest text-text/40">
          Players
        </span>
        <div
          className={
            laneList.length > 4
              ? 'grid grid-cols-2 gap-2'
              : 'flex flex-col gap-3'
          }
        >
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
              const compact = laneList.length > 4
              return (
                <motion.div
                  key={lane.puck_id}
                  layout
                  initial={{ y: 10, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: -10, opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  className={`flex items-center rounded-2xl border-2 ${
                    isWinningLane ? 'border-correct' : 'border-text/10'
                  } bg-text/5 ${compact ? 'gap-2 px-2 py-2' : 'gap-3 px-4 py-3'}`}
                  style={isWinningLane ? { boxShadow: '0 0 30px rgba(251,191,36,0.4)' } : undefined}
                >
                  <div
                    className={`flex flex-none items-center justify-center rounded-full font-display ${
                      compact ? 'h-9 w-9 text-lg' : 'h-12 w-12 text-2xl'
                    }`}
                    style={{ backgroundColor: lane.color, color: '#0A0E1A' }}
                  >
                    {lane.puck_id}
                  </div>
                  <div className="flex flex-1 flex-col overflow-hidden">
                    <span className={`font-body font-bold text-text ${compact ? 'text-sm' : 'text-base'}`}>
                      Puck {lane.puck_id}
                    </span>
                    <span className={`truncate font-body ${stateColorClass} ${compact ? 'text-xs' : 'text-sm'}`}>
                      {stateLabel}
                    </span>
                  </div>
                  <div className="flex-none text-right">
                    <span className={`font-mono font-bold text-text ${compact ? 'text-base' : 'text-xl'}`}>
                      {lane.cumulative.toLocaleString()}
                    </span>
                  </div>
                </motion.div>
              )
            })}
          </AnimatePresence>
        </div>
        {laneList.length === 0 ? (
          <p className="font-body text-base text-text/50">No players yet…</p>
        ) : null}
      </aside>
    </main>
  )
}
