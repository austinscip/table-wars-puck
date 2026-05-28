import { motion } from 'framer-motion'

/**
 * Atmospheric backdrop used on the title-adjacent kiosk screens
 * (Title / Lobby / CategoryPick / Scoreboard). Radial gradient from
 * center to deep navy plus two color glows that breathe in/out so the
 * screen never sits completely still in a busy bar room. Pointer-events
 * none so it never intercepts a click.
 *
 * Tuned to be subtle — strong enough to feel alive from across the
 * room, never garish enough to distract from the content above.
 */
interface Props {
  /** Top-left glow color (rgba with ~0.16-0.20 alpha). */
  glowA?: string
  /** Bottom-right glow color (rgba with ~0.14-0.18 alpha). */
  glowB?: string
}

export default function AmbientBackground({
  glowA = 'rgba(59,130,246,0.18)',
  glowB = 'rgba(236,72,153,0.16)',
}: Props) {
  return (
    <>
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse at center, #1A2238 0%, #0A0E1A 65%, #050811 100%)',
        }}
      />
      <motion.div
        className="pointer-events-none absolute left-[-10%] top-[-10%] h-[40vw] w-[40vw] rounded-full"
        style={{ background: `radial-gradient(circle, ${glowA}, transparent 60%)` }}
        animate={{ scale: [1, 1.15, 1], opacity: [0.6, 0.9, 0.6] }}
        transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="pointer-events-none absolute right-[-10%] bottom-[-15%] h-[45vw] w-[45vw] rounded-full"
        style={{ background: `radial-gradient(circle, ${glowB}, transparent 65%)` }}
        animate={{ scale: [1.1, 1, 1.1], opacity: [0.5, 0.85, 0.5] }}
        transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut' }}
      />
    </>
  )
}
