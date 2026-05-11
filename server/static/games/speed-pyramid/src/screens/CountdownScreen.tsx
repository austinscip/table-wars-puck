import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'

/**
 * Placeholder Countdown screen — fully fleshed out in slice 1C. For
 * slice 1B we just need a navigation destination after pairing so we
 * can prove the `paired` event end-to-end.
 */
export default function CountdownScreen() {
  const { sessionCode } = useParams<{ sessionCode: string }>()
  return (
    <main className="flex h-full w-full flex-col items-center justify-center gap-12 px-8 py-16">
      <motion.h1
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.34, 1.56, 0.64, 1] }}
        className="font-display text-[clamp(6rem,18vw,16rem)] leading-none tracking-tight text-correct"
      >
        PAIRED
      </motion.h1>
      <p className="font-mono text-2xl text-text/70">
        session_code: <span className="text-text">{sessionCode}</span>
      </p>
      <p className="font-body text-xl text-text/50">
        Countdown screen lands in slice 1C.
      </p>
    </main>
  )
}
