import { motion } from 'framer-motion'

interface Props {
  tier: string | null
  points: number
}

const COLOR_FOR_TIER: Record<string, string> = {
  LEGENDARY: 'text-correct',
  EXPERT: 'text-primary',
  AVERAGE: 'text-accent',
  TIMEOUT: 'text-text/40',
  WRONG: 'text-wrong',
}

export default function TierBadge({ tier, points }: Props) {
  if (!tier) return null
  const color = COLOR_FOR_TIER[tier] ?? 'text-text'

  return (
    <motion.div
      initial={{ scale: 0.5, opacity: 0, y: 30 }}
      animate={{ scale: 1, opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.34, 1.56, 0.64, 1] }}
      className="flex flex-col items-center gap-3"
    >
      <span className={`font-display text-[clamp(3rem,8vw,7rem)] leading-none ${color}`}>
        {tier}
      </span>
      <span className="font-mono text-3xl font-bold text-text/80">
        {points >= 0 ? '+' : ''}
        {points}
      </span>
    </motion.div>
  )
}
