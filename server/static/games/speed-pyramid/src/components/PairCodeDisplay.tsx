import { motion, AnimatePresence } from 'framer-motion'

interface Props {
  /** Six-digit pair code as a string (may include leading zeros). */
  code: string
  /** Per-slot dial progress reported by the puck. null = not yet dialed. */
  progress: (number | null)[]
}

/**
 * Renders the 6-digit pair code on the TV.
 *
 * - Slots that haven't been dialed yet show the target digit in dim/muted
 *   color so the player can read what to dial.
 * - As the puck dials each digit (server emits `pair_dial_progress`), the
 *   matching slot animates: dialed digits highlight in --color-primary,
 *   wrong digits in --color-wrong, with an overshoot scale-in.
 */
export default function PairCodeDisplay({ code, progress }: Props) {
  const digits = code.split('')
  return (
    <div className="flex flex-row items-center justify-center gap-4 md:gap-8">
      {digits.map((target, i) => {
        const dialed = progress[i]
        const isCorrect = dialed === Number(target)
        const isWrong = dialed !== null && dialed !== undefined && !isCorrect
        const isDialed = dialed !== null && dialed !== undefined

        const colorClass = isCorrect
          ? 'text-primary'
          : isWrong
          ? 'text-wrong'
          : 'text-text/40'

        return (
          <div
            key={i}
            className="relative flex h-[clamp(8rem,15vw,18rem)] w-[clamp(5rem,10vw,12rem)] items-center justify-center rounded-3xl border-2 border-text/10 bg-text/5"
          >
            <AnimatePresence mode="wait">
              <motion.span
                key={isDialed ? `d-${dialed}` : `t-${target}`}
                initial={{ scale: 0.4, opacity: 0, y: 30 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                exit={{ scale: 0.4, opacity: 0, y: -30 }}
                transition={{
                  duration: 0.35,
                  ease: [0.34, 1.56, 0.64, 1],
                }}
                className={`font-mono text-[clamp(4rem,9vw,11rem)] font-bold leading-none ${colorClass}`}
              >
                {isDialed ? dialed : target}
              </motion.span>
            </AnimatePresence>
          </div>
        )
      })}
    </div>
  )
}
