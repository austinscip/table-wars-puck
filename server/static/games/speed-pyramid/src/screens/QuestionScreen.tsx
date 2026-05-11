import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { getSocket } from '../lib/socket'
import { api, type SpeedPyramidQuestion } from '../lib/api'
import { audio } from '../lib/audio'
import AnswerPill from '../components/AnswerPill'
import TimerBar from '../components/TimerBar'
import TierBadge from '../components/TierBadge'

type Phase = 'awaiting_question' | 'answering' | 'locked' | 'reveal'

interface QuestionShowEvent {
  session_code: string
  question: SpeedPyramidQuestion
  round: number
  total_rounds: number
  started_at: number
}

interface AnswerLockedEvent {
  session_code: string
  puck_id: number
  answer: 'A' | 'B' | 'C' | 'D'
  question_id: number
}

interface RevealEvent {
  session_code: string
  puck_id: number
  question_id: number
  is_correct: boolean
  correct_answer: 'A' | 'B' | 'C' | 'D'
  submitted_answer: 'A' | 'B' | 'C' | 'D'
  points: number
  tier: string | null
  response_time_ms: number
}

const REVEAL_HOLD_MS = 2500

/**
 * QuestionScreen — TV view for an in-flight Speed Pyramid match.
 *
 *  1. Joins Socket.IO room=session_code on mount.
 *  2. Immediately POSTs /api/sp/load-question to ask the server for Q1
 *     (or the next question after a reveal).
 *  3. Renders the question + 4 AnswerPills + TimerBar via 'question_show'.
 *  4. Highlights the locked pill via 'answer_locked'.
 *  5. Shows correct/wrong + tier badge via 'reveal'. After REVEAL_HOLD_MS
 *     auto-advances by requesting the next question. After round
 *     SP_TOTAL_ROUNDS, server emits 'match_ended' -> navigate to scoreboard.
 */
export default function QuestionScreen() {
  const navigate = useNavigate()
  const { sessionCode } = useParams<{ sessionCode: string }>()
  const [params] = useSearchParams()
  const isDemo = params.get('demo') === '1'
  // Demo-mode: simulate a puck answering after a randomized delay so
  // the match plays through end-to-end on a laptop without firmware.
  const puckId = Number(params.get('puck_id') ?? '99')

  const [question, setQuestion] = useState<SpeedPyramidQuestion | null>(null)
  const [round, setRound] = useState<number>(0)
  const [totalRounds, setTotalRounds] = useState<number>(7)
  const [startedAt, setStartedAt] = useState<number>(0)
  const [phase, setPhase] = useState<Phase>('awaiting_question')
  const [lockedAnswer, setLockedAnswer] = useState<'A' | 'B' | 'C' | 'D' | null>(null)
  const [reveal, setReveal] = useState<RevealEvent | null>(null)
  // Track which tick boundaries we've already played so the countdown
  // tone fires exactly once per second in the last 3s.
  const lastTickRef = useRef<number>(-1)
  // Demo-mode: track which questions we've auto-answered so we don't
  // double-submit if React re-renders the same question.
  const demoAnsweredRef = useRef<Set<number>>(new Set())

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
      setLockedAnswer(null)
      setReveal(null)
      lastTickRef.current = -1
      audio.questionShow()

      // Demo-mode autoplay: randomly pick A/B/C/D after a 1.2-3.0s delay
      // and POST /api/trivia/answer so the match advances without a puck.
      // Roughly 70% correct so the scoreboard looks interesting.
      if (isDemo && !demoAnsweredRef.current.has(p.question.id)) {
        demoAnsweredRef.current.add(p.question.id)
        const letters = ['A', 'B', 'C', 'D'] as const
        const delay = 1200 + Math.random() * 1800
        window.setTimeout(() => {
          // We don't know the correct answer client-side without a DB
          // peek, so we just pick uniformly and let the server score.
          const answer = letters[Math.floor(Math.random() * 4)]
          const elapsedMs = Date.now() - p.started_at * 1000
          void fetch('/api/trivia/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              session_code: sessionCode,
              puck_id: puckId,
              question_id: p.question.id,
              answer,
              response_time_ms: Math.max(0, Math.round(elapsedMs)),
            }),
          })
        }, delay)
      }
    }
    function onAnswerLocked(p: AnswerLockedEvent) {
      if (p.session_code !== sessionCode) return
      setLockedAnswer(p.answer)
      setPhase('locked')
      audio.lockIn()
    }
    function onReveal(p: RevealEvent) {
      if (p.session_code !== sessionCode) return
      setReveal(p)
      setPhase('reveal')
      audio.reveal()
      window.setTimeout(() => {
        if (p.is_correct) audio.correct()
        else audio.wrong()
      }, 120)
      // Auto-advance to next question (or end of match) after the hold.
      setTimeout(() => {
        api.sp
          .loadQuestion(sessionCode)
          .catch(() => navigate(`/scoreboard/${sessionCode}`))
      }, REVEAL_HOLD_MS)
    }
    function onMatchEnded() {
      navigate(`/scoreboard/${sessionCode}`)
    }

    socket.on('question_show', onQuestionShow)
    socket.on('answer_locked', onAnswerLocked)
    socket.on('reveal', onReveal)
    socket.on('match_ended', onMatchEnded)

    // Kick off the first question. If we entered this screen after a
    // reload mid-match, the server might be a round in already — that's
    // fine, the next load will pick up the next round.
    api.sp.loadQuestion(sessionCode).catch(() => {})

    return () => {
      socket.off('question_show', onQuestionShow)
      socket.off('answer_locked', onAnswerLocked)
      socket.off('reveal', onReveal)
      socket.off('match_ended', onMatchEnded)
    }
  }, [sessionCode, navigate])

  // Drive countdown ticks during the last 3s of the answering phase.
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

  const stateFor = (letter: 'A' | 'B' | 'C' | 'D') => {
    if (phase === 'reveal' && reveal) {
      if (letter === reveal.correct_answer) return 'correct' as const
      if (letter === reveal.submitted_answer) return 'wrong' as const
      return 'dim' as const
    }
    if (lockedAnswer === letter) return 'locked' as const
    return 'idle' as const
  }

  return (
    <main className="flex h-full w-full flex-col gap-8 px-12 py-10">
      <header className="flex items-baseline justify-between">
        <span className="font-display text-3xl tracking-wide text-text/70">
          {question.category_emoji} {question.category}
        </span>
        <span className="font-mono text-2xl text-text/60">
          Q{round} / {totalRounds}
        </span>
      </header>

      <TimerBar
        durationSec={question.time_limit}
        startedAt={startedAt}
        frozen={phase === 'locked' || phase === 'reveal'}
      />

      <motion.h1
        key={question.id}
        initial={{ y: 30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.45, ease: [0.34, 1.56, 0.64, 1] }}
        className="font-display text-[clamp(3rem,7vw,7rem)] leading-tight tracking-tight text-text"
      >
        {question.question}
      </motion.h1>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {(['A', 'B', 'C', 'D'] as const).map((letter, i) => (
          <AnswerPill
            key={letter}
            letter={letter}
            text={question.answers[letter]}
            state={stateFor(letter)}
            index={i}
          />
        ))}
      </div>

      <AnimatePresence>
        {phase === 'reveal' && reveal ? (
          <motion.div
            key="tier"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex items-center justify-center bg-bg/85 backdrop-blur-sm"
          >
            <TierBadge tier={reveal.tier} points={reveal.points} />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </main>
  )
}
