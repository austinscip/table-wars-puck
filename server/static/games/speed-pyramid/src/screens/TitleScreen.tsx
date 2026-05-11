import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'

export default function TitleScreen() {
  const navigate = useNavigate()

  return (
    <main className="flex h-full w-full flex-col items-center justify-center px-8 py-16">
      <motion.h1
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }}
        className="font-display text-[clamp(6rem,18vw,16rem)] leading-none tracking-tight text-text"
      >
        SPEED PYRAMID
      </motion.h1>

      <motion.p
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.3, ease: 'easeOut' }}
        className="mt-8 font-body text-2xl font-medium tracking-wide text-text/70"
      >
        Hold the puck button to pair.
      </motion.p>

      {/* Demo-mode click-through. Lets a laptop run the full match
          without a real puck — useful for previews and visual review.
          Real bar deployments ignore this and use the puck flow. */}
      <motion.button
        type="button"
        onClick={() => navigate('/pair?puck_id=99&demo=1')}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 1.2 }}
        className="mt-16 cursor-pointer rounded-2xl border-2 border-primary/40 px-8 py-4 font-body text-xl font-medium text-primary transition hover:border-primary hover:bg-primary/10"
      >
        Demo mode — no puck
      </motion.button>
    </main>
  )
}
