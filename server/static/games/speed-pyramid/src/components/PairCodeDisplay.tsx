import { motion, AnimatePresence } from 'framer-motion'

interface Props {
  /** Six-digit pair code as a string (may include leading zeros). */
  code: string
  /** Per-slot dial progress reported by the puck. null = not yet dialed. */
  progress: (number | null)[]
  /** Active slot the puck is currently dialing (0..5). */
  activeSlot: number
  /** Live preview digit the puck currently has selected at activeSlot. */
  previewDigit: number | null
}

/**
 * Two-row pair display:
 *
 *   Target row (top):   the 6 digits the player must dial (dim until done).
 *                       Active slot is highlighted so the player knows
 *                       which one to dial next.
 *   Input row (bottom): the player's actual entries. Locked slots show the
 *                       dialed digit. Current slot shows a live preview of
 *                       whatever the puck is on RIGHT NOW (before the tap).
 *                       Unfilled future slots show "_".
 */
export default function PairCodeDisplay({
  code,
  progress,
  activeSlot,
  previewDigit,
}: Props) {
  const targets = code.split('')

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Target row */}
      <div className="flex flex-col items-center gap-2">
        <span className="font-body text-base font-medium uppercase tracking-widest text-text/40">
          Target
        </span>
        <div className="flex flex-row items-center justify-center gap-3 md:gap-6">
          {targets.map((target, i) => {
            const isActive = i === activeSlot
            const isDone = progress[i] !== null && progress[i] !== undefined
            const colorClass = isDone
              ? 'text-text/20'
              : isActive
              ? 'text-accent'
              : 'text-text/50'
            const borderClass = isActive
              ? 'border-accent'
              : 'border-text/10'
            return (
              <div
                key={i}
                className={`flex h-[clamp(5rem,9vw,11rem)] w-[clamp(3rem,6vw,8rem)] items-center justify-center rounded-2xl border-2 ${borderClass}`}
              >
                <span
                  className={`font-mono text-[clamp(2.5rem,5vw,7rem)] font-bold leading-none ${colorClass}`}
                >
                  {target}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Input row */}
      <div className="flex flex-col items-center gap-2">
        <span className="font-body text-base font-medium uppercase tracking-widest text-text/40">
          Your input
        </span>
        <div className="flex flex-row items-center justify-center gap-3 md:gap-6">
          {targets.map((target, i) => {
            const locked = progress[i]
            const isLocked = locked !== null && locked !== undefined
            const isActive = i === activeSlot
            const showPreview = isActive && previewDigit !== null
            const display = isLocked
              ? String(locked)
              : showPreview
              ? String(previewDigit)
              : '_'

            const isCorrect = isLocked && locked === Number(target)
            const isWrong = isLocked && !isCorrect
            const colorClass = isCorrect
              ? 'text-correct'
              : isWrong
              ? 'text-wrong'
              : isActive
              ? 'text-primary'
              : 'text-text/30'
            const ringClass =
              isActive && !isLocked ? 'ring-2 ring-primary' : ''

            return (
              <div
                key={i}
                className={`flex h-[clamp(6rem,11vw,14rem)] w-[clamp(4rem,8vw,10rem)] items-center justify-center rounded-2xl border-2 border-text/10 bg-text/5 ${ringClass}`}
              >
                <AnimatePresence mode="wait">
                  <motion.span
                    key={`${i}-${display}`}
                    initial={{ scale: 0.4, opacity: 0, y: 16 }}
                    animate={{ scale: 1, opacity: 1, y: 0 }}
                    exit={{ scale: 0.4, opacity: 0, y: -16 }}
                    transition={{
                      duration: 0.2,
                      ease: [0.34, 1.56, 0.64, 1],
                    }}
                    className={`font-mono text-[clamp(3rem,7vw,9rem)] font-bold leading-none ${colorClass}`}
                  >
                    {display}
                  </motion.span>
                </AnimatePresence>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
