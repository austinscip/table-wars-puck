import { useEffect, useState } from 'react'

interface Props {
  to: number
  /** Total animation duration in ms. */
  durationMs?: number
  /** Delay before the count-up starts, in ms (for staggering). */
  delayMs?: number
  className?: string
}

/**
 * Numeric count-up. Eases out so the last digits land slow. Uses
 * requestAnimationFrame — no library dependency.
 */
export default function CountUpScore({
  to,
  durationMs = 1200,
  delayMs = 0,
  className,
}: Props) {
  const [value, setValue] = useState(0)

  useEffect(() => {
    let raf = 0
    let start = 0
    const ease = (t: number) => 1 - Math.pow(1 - t, 3)

    function tick(now: number) {
      if (!start) start = now
      const elapsed = now - start - delayMs
      if (elapsed < 0) {
        raf = requestAnimationFrame(tick)
        return
      }
      const t = Math.min(1, elapsed / durationMs)
      setValue(Math.round(ease(t) * to))
      if (t < 1) raf = requestAnimationFrame(tick)
    }

    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [to, durationMs, delayMs])

  return <span className={className}>{value.toLocaleString()}</span>
}
