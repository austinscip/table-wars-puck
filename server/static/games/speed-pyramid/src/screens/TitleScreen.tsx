import { motion } from 'framer-motion'
import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { audio } from '../lib/audio'
import { getSocket } from '../lib/socket'

interface PairStartedEvent {
  puck_id: number
  pair_code: string
}

export default function TitleScreen() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  // The 'Demo mode' click-through only renders when the URL explicitly
  // opts in via ?dev=1. Production bar TVs land at /tv/speed-pyramid
  // with no params and see only the title + 'Hold the puck button to
  // pair.' subtitle — so customers can't bypass the puck flow.
  const showDemo = params.get('dev') === '1'

  // Subscribe to the global 'lobby' room. When ANY puck POSTs
  // /api/pair/request, server emits 'pair_started' with the puck_id —
  // we auto-advance to that puck's pair page. Real-flow advance happens
  // here, not on a timer, so the title screen truly waits for the puck
  // button to be held.
  useEffect(() => {
    const socket = getSocket()
    socket.emit('join_lobby')

    function onPairStarted(p: PairStartedEvent) {
      navigate(`/pair?puck_id=${p.puck_id}`)
    }
    socket.on('pair_started', onPairStarted)

    return () => {
      socket.off('pair_started', onPairStarted)
    }
  }, [navigate])

  return (
    <main className="relative flex h-full w-full flex-col items-center justify-center overflow-hidden px-8 py-16">
      {/* Atmospheric background. Radial gradient from center + subtle
          accent glows in primary / accent so the title room feels alive
          instead of flat navy. Pointer-events none so nothing blocks the
          dev-mode demo button below. */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse at center, #1A2238 0%, #0A0E1A 65%, #050811 100%)',
        }}
      />
      <motion.div
        className="pointer-events-none absolute left-[-10%] top-[-10%] h-[40vw] w-[40vw] rounded-full"
        style={{ background: 'radial-gradient(circle, rgba(59,130,246,0.18), transparent 60%)' }}
        animate={{ scale: [1, 1.15, 1], opacity: [0.6, 0.9, 0.6] }}
        transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="pointer-events-none absolute right-[-10%] bottom-[-15%] h-[45vw] w-[45vw] rounded-full"
        style={{ background: 'radial-gradient(circle, rgba(236,72,153,0.16), transparent 65%)' }}
        animate={{ scale: [1.1, 1, 1.1], opacity: [0.5, 0.85, 0.5] }}
        transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* Wordmark — glow + breathing scale so it feels animated rather
          than printed. Stacked text-shadow gives depth at TV viewing
          distance without needing a heavier 3D library. */}
      <motion.h1
        initial={{ y: 60, opacity: 0, scale: 0.94 }}
        animate={{ y: 0, opacity: 1, scale: [1, 1.015, 1] }}
        transition={{
          y: { duration: 0.8, ease: [0.34, 1.56, 0.64, 1] },
          opacity: { duration: 0.8 },
          scale: { duration: 4.5, repeat: Infinity, ease: 'easeInOut', delay: 0.9 },
        }}
        className="relative z-10 font-display text-[clamp(6rem,18vw,16rem)] leading-none tracking-tight text-text"
        style={{
          textShadow:
            '0 0 40px rgba(251,191,36,0.22), 0 0 90px rgba(251,191,36,0.12), 0 4px 20px rgba(0,0,0,0.5)',
        }}
      >
        SPEED PYRAMID
      </motion.h1>

      {/* Pair-instruction subtitle pulses gently so the screen never sits
          completely still in a busy bar room. */}
      <motion.p
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: [0.55, 0.85, 0.55] }}
        transition={{
          y: { duration: 0.5, delay: 0.5, ease: 'easeOut' },
          opacity: { duration: 3, repeat: Infinity, ease: 'easeInOut', delay: 1.2 },
        }}
        className="relative z-10 mt-10 font-body text-2xl font-medium tracking-wide text-text"
      >
        Hold the puck button to pair.
      </motion.p>

      {/* Three breathing dots underneath — the "ready, waiting" indicator
          used by jukeboxes and idle kiosks. Each lights in succession. */}
      <div className="relative z-10 mt-8 flex gap-3">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="block h-2 w-2 rounded-full bg-text"
            initial={{ opacity: 0.2 }}
            animate={{ opacity: [0.2, 1, 0.2] }}
            transition={{
              duration: 1.6,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: 0.2 * i,
            }}
          />
        ))}
      </div>

      {/* Demo-mode click-through. Only rendered when the URL has
          ?dev=1. Real bar deployments hit /tv/speed-pyramid without
          params and see only the title + pair-instructions. */}
      {showDemo ? (
        <motion.button
          type="button"
          onClick={() => {
            // Prime the AudioContext on this real user gesture so the
            // procedural Web Audio tones (question_show / lockIn / etc.)
            // play through the rest of the match. Browsers will not
            // start audio from a Socket.IO event handler alone.
            audio.unlock()
            navigate('/pair?puck_id=99&demo=1')
          }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 1.2 }}
          className="mt-16 cursor-pointer rounded-2xl border-2 border-primary/40 px-8 py-4 font-body text-xl font-medium text-primary transition hover:border-primary hover:bg-primary/10"
        >
          Demo mode — no puck
        </motion.button>
      ) : null}
    </main>
  )
}
