import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { audio } from '../lib/audio'

const STEPS = ['GET READY', '3', '2', '1', 'GO!']
const STEP_MS = 900

/**
 * 3-2-1 countdown after a successful pair, then jumps to /question/:code
 * which subscribes to socket events and asks the server for Q1.
 * Preserves the ?demo=1 flag if present so QuestionScreen knows to
 * auto-answer.
 */
export default function CountdownScreen() {
  const { sessionCode } = useParams<{ sessionCode: string }>()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    if (!sessionCode) return
    if (stepIndex >= STEPS.length) {
      const qs = params.get('demo') === '1'
        ? `?demo=1&puck_id=${params.get('puck_id') ?? '99'}`
        : ''
      navigate(`/question/${sessionCode}${qs}`)
      return
    }
    // R017: audio on each countdown step. GO! gets the final-tick
    // urgency cue; everything else is the regular soft tick.
    const label = STEPS[stepIndex]
    if (label === 'GO!') audio.tickFinal()
    else if (label === 'GET READY') audio.reveal()
    else audio.tick()
    const t = window.setTimeout(() => setStepIndex(stepIndex + 1), STEP_MS)
    return () => window.clearTimeout(t)
  }, [stepIndex, sessionCode, navigate, params])

  const label = STEPS[stepIndex] ?? ''
  const isGo = label === 'GO!'

  return (
    <main className="flex h-full w-full flex-col items-center justify-center gap-8 px-8 py-16">
      <p className="font-mono text-2xl text-text/60">
        session: {sessionCode}
      </p>
      <AnimatePresence mode="wait">
        <motion.div
          key={label}
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 1.6, opacity: 0 }}
          transition={{ duration: 0.45, ease: [0.34, 1.56, 0.64, 1] }}
          className={`font-display text-[clamp(8rem,22vw,20rem)] leading-none tracking-tight ${
            isGo ? 'text-correct' : 'text-text'
          }`}
        >
          {label}
        </motion.div>
      </AnimatePresence>
    </main>
  )
}
