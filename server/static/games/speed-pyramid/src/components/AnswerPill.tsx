import { AnimatePresence, motion } from 'framer-motion'

type State = 'idle' | 'preview' | 'locked' | 'correct' | 'wrong' | 'dim'

interface PreviewMarker {
  puck_id: number
  color: string
}

interface Props {
  letter: 'A' | 'B' | 'C' | 'D'
  text: string
  state: State
  /** Stagger delay in seconds for entrance animation. */
  index: number
  /** Live aim markers — pucks currently hovering this answer. Shown as
   *  colored dots in the top-right of the pill so the room sees each
   *  player's tilt in real time, not just their final lock. */
  previewBy?: PreviewMarker[]
}

const STYLES: Record<State, string> = {
  idle: 'bg-text/5 text-text border-text/15',
  preview: 'bg-primary/10 text-text border-primary/50',
  locked: 'bg-primary/20 text-primary border-primary',
  correct: 'bg-correct/20 text-correct border-correct',
  wrong: 'bg-wrong/15 text-wrong border-wrong',
  dim: 'bg-text/5 text-text/30 border-text/10',
}

export default function AnswerPill({
  letter,
  text,
  state,
  index,
  previewBy = [],
}: Props) {
  const ring =
    state === 'correct'
      ? '0 0 40px rgba(251, 191, 36, 0.45)'
      : state === 'wrong'
      ? '0 0 30px rgba(239, 68, 68, 0.35)'
      : state === 'locked'
      ? '0 0 30px rgba(59, 130, 246, 0.45)'
      : state === 'preview'
      ? '0 0 18px rgba(59, 130, 246, 0.25)'
      : 'none'

  return (
    <motion.div
      initial={{ y: 40, opacity: 0 }}
      animate={{
        y: 0,
        opacity: 1,
        scale:
          state === 'correct' || state === 'locked'
            ? 1.04
            : state === 'preview'
            ? 1.02
            : 1,
        boxShadow: ring,
      }}
      transition={{
        duration: 0.45,
        delay: 0.08 * index,
        ease: [0.34, 1.56, 0.64, 1],
      }}
      className={`relative flex items-center gap-6 overflow-hidden rounded-2xl border-2 px-8 py-6 ${STYLES[state]}`}
      style={{
        // Subtle inner gradient so the card isn't a flat colored rectangle.
        backgroundImage:
          'linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0) 60%)',
      }}
    >
      <span className="font-display text-[clamp(2.5rem,5vw,4.5rem)] leading-none">
        {letter}
      </span>
      <span className="font-body text-[clamp(1.25rem,2.4vw,2.5rem)] font-medium leading-tight">
        {text}
      </span>

      {/* Live aim markers — colored dots, one per puck currently
          hovering THIS answer. Pop in/out as pucks tilt. Hidden during
          reveal so they don't compete with the correct/wrong stinger. */}
      {state !== 'correct' && state !== 'wrong' && (
        <div className="pointer-events-none absolute right-4 top-4 flex flex-wrap gap-1.5">
          <AnimatePresence>
            {previewBy.map((p) => (
              <motion.span
                key={p.puck_id}
                initial={{ scale: 0.3, opacity: 0 }}
                animate={{ scale: 1, opacity: 0.95 }}
                exit={{ scale: 0.3, opacity: 0 }}
                transition={{ duration: 0.18, ease: [0.34, 1.56, 0.64, 1] }}
                className="block h-3 w-3 rounded-full ring-2 ring-bg"
                style={{
                  backgroundColor: p.color,
                  boxShadow: `0 0 12px ${p.color}`,
                }}
                title={`Puck ${p.puck_id} aiming here`}
              />
            ))}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  )
}
