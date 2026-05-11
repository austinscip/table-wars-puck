import { motion } from 'framer-motion'

export default function TitleScreen() {
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
    </main>
  )
}
