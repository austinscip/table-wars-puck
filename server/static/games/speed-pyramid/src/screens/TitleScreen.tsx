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
