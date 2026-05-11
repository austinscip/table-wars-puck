import { motion } from 'framer-motion'

type State = 'idle' | 'locked' | 'correct' | 'wrong' | 'dim'

interface Props {
  letter: 'A' | 'B' | 'C' | 'D'
  text: string
  state: State
  /** Stagger delay in seconds for entrance animation. */
  index: number
}

const STYLES: Record<State, string> = {
  idle: 'bg-text/5 text-text border-text/15',
  locked: 'bg-primary/15 text-primary border-primary',
  correct: 'bg-correct/20 text-correct border-correct',
  wrong: 'bg-wrong/15 text-wrong border-wrong',
  dim: 'bg-text/5 text-text/30 border-text/10',
}

export default function AnswerPill({ letter, text, state, index }: Props) {
  const ring =
    state === 'correct'
      ? '0 0 40px rgba(251, 191, 36, 0.45)'
      : state === 'wrong'
      ? '0 0 30px rgba(239, 68, 68, 0.35)'
      : state === 'locked'
      ? '0 0 30px rgba(59, 130, 246, 0.45)'
      : 'none'

  return (
    <motion.div
      initial={{ y: 40, opacity: 0 }}
      animate={{
        y: 0,
        opacity: 1,
        scale: state === 'correct' || state === 'locked' ? 1.04 : 1,
        boxShadow: ring,
      }}
      transition={{
        duration: 0.45,
        delay: 0.08 * index,
        ease: [0.34, 1.56, 0.64, 1],
      }}
      className={`flex items-center gap-6 rounded-2xl border-2 px-8 py-6 ${STYLES[state]}`}
    >
      <span className="font-display text-[clamp(2.5rem,5vw,4.5rem)] leading-none">
        {letter}
      </span>
      <span className="font-body text-[clamp(1.25rem,2.4vw,2.5rem)] font-medium leading-tight">
        {text}
      </span>
    </motion.div>
  )
}
