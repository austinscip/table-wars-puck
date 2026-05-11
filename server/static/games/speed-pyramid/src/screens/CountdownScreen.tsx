import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

const STEPS = ['GET READY', '3', '2', '1', 'GO!']
const STEP_MS = 900

/**
 * 3-2-1 countdown after a successful pair, then jumps to /question/:code
 * which subscribes to socket events and asks the server for Q1.
 */
export default function CountdownScreen() {
  const { sessionCode } = useParams<{ sessionCode: string }>()
  const navigate = useNavigate()
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    if (!sessionCode) return
    if (stepIndex >= STEPS.length) {
      navigate(`/question/${sessionCode}`)
      return
    }
    const t = window.setTimeout(() => setStepIndex(stepIndex + 1), STEP_MS)
    return () => window.clearTimeout(t)
  }, [stepIndex, sessionCode, navigate])

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
