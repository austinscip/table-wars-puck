import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'

interface Props {
  /** Total time available in seconds. */
  durationSec: number
  /** Server-side timestamp (epoch seconds) when the question started. */
  startedAt: number
  /** If true, the bar freezes (answer locked / reveal in progress). */
  frozen?: boolean
}

/**
 * Depleting horizontal bar. Drives off wall-clock `startedAt` from the
 * server so it stays in sync even after a reconnect. Bar color shifts
 * from --color-accent (pink) to --color-wrong as time runs out.
 */
export default function TimerBar({ durationSec, startedAt, frozen }: Props) {
  const [remainingMs, setRemainingMs] = useState(() => {
    const elapsed = (Date.now() / 1000 - startedAt) * 1000
    return Math.max(0, durationSec * 1000 - elapsed)
  })

  useEffect(() => {
    if (frozen) return
    let raf = 0
    const tick = () => {
      const elapsed = (Date.now() / 1000 - startedAt) * 1000
      const rem = Math.max(0, durationSec * 1000 - elapsed)
      setRemainingMs(rem)
      if (rem > 0) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [durationSec, startedAt, frozen])

  const pct = (remainingMs / (durationSec * 1000)) * 100
  const danger = pct < 30
  const color = danger ? 'var(--color-wrong)' : 'var(--color-accent)'

  return (
    <div className="relative h-3 w-full overflow-hidden rounded-full bg-text/10">
      <motion.div
        className="absolute inset-y-0 left-0 rounded-full"
        animate={{ width: `${pct}%`, backgroundColor: color }}
        transition={{ ease: 'linear', duration: 0.1 }}
      />
    </div>
  )
}
