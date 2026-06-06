import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { pctRemaining } from '../lib/num'

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
 * server so it stays in sync even after a reconnect. The bar fills with
 * a gradient (accent → primary) under normal time, shifts to a wrong-red
 * gradient in the final 30%, glows at its leading edge, and pulses when
 * time is critical so the room feels urgency from across a bar.
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

  // Guarded so a degenerate/zero duration can't produce NaN%/Infinity% and
  // blank the bar on the unattended TV (audit tv-speed-pyramid-web).
  const pct = pctRemaining(remainingMs, durationSec * 1000)
  const danger = pct < 30
  const critical = pct < 15

  // Gradient: full color spectrum until danger, then red-hot.
  const fill = danger
    ? 'linear-gradient(90deg, #ef4444 0%, #f59e0b 100%)'
    : 'linear-gradient(90deg, #ec4899 0%, #3b82f6 100%)'

  return (
    <div className="relative h-3 w-full overflow-hidden rounded-full bg-text/10 ring-1 ring-white/5">
      <motion.div
        className="absolute inset-y-0 left-0 rounded-full"
        animate={{
          width: `${pct}%`,
          backgroundImage: fill,
          // Tighten the pulse as time runs out; freeze when locked.
          opacity: critical && !frozen ? [1, 0.55, 1] : 1,
        }}
        transition={{
          width: { ease: 'linear', duration: 0.1 },
          backgroundImage: { duration: 0.4 },
          opacity: critical && !frozen
            ? { duration: 0.55, repeat: Infinity, ease: 'easeInOut' }
            : { duration: 0.2 },
        }}
        style={{
          boxShadow: danger
            ? '0 0 20px rgba(239,68,68,0.55), 0 0 6px rgba(239,68,68,0.7) inset'
            : '0 0 18px rgba(59,130,246,0.35)',
        }}
      />
      {/* Leading-edge glow head — sits at the current bar tip so the eye
          tracks depletion. Hidden once the bar is fully drained or frozen. */}
      {!frozen && pct > 0.5 && (
        <motion.span
          className="pointer-events-none absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full"
          animate={{ left: `${pct}%` }}
          transition={{ ease: 'linear', duration: 0.1 }}
          style={{
            background: danger
              ? 'radial-gradient(circle, rgba(239,68,68,0.9) 0%, rgba(239,68,68,0) 70%)'
              : 'radial-gradient(circle, rgba(255,255,255,0.85) 0%, rgba(255,255,255,0) 70%)',
          }}
        />
      )}
    </div>
  )
}
