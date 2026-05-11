import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../lib/api'
import { getSocket } from '../lib/socket'
import PairCodeDisplay from '../components/PairCodeDisplay'

interface DialProgressEvent {
  puck_id: number
  digit_index: number
  digit: number
  progress: (number | null)[]
}

interface PairedEvent {
  puck_id: number
  session_code: string
}

/**
 * Pair screen — first stop after the TV navigates here. Behavior:
 *
 *  1. On mount, calls POST /api/pair/request with the URL puck_id param,
 *     receives a 6-digit pair_code, joins Socket.IO room=pair_code.
 *  2. Renders the 6 target digits via PairCodeDisplay. As the puck dials
 *     digits (server emits `pair_dial_progress`), each slot animates.
 *  3. When the puck confirms (server emits `paired`), navigates to
 *     /countdown/<session_code>.
 */
export default function PairScreen() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const puckId = Number(params.get('puck_id') ?? '1')

  const [code, setCode] = useState<string | null>(null)
  const [progress, setProgress] = useState<(number | null)[]>(
    () => Array(6).fill(null) as (number | null)[],
  )
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const socket = getSocket()

    async function start() {
      try {
        const res = await api.pair.request(puckId)
        if (!active) return
        setCode(res.pair_code)
        socket.emit('join_pair_room', { pair_code: res.pair_code })
      } catch (e) {
        if (!active) return
        setError((e as Error).message)
      }
    }
    start()

    function onProgress(payload: DialProgressEvent) {
      if (payload.puck_id !== puckId) return
      setProgress(payload.progress)
    }
    function onPaired(payload: PairedEvent) {
      if (payload.puck_id !== puckId) return
      navigate(`/countdown/${payload.session_code}`)
    }

    socket.on('pair_dial_progress', onProgress)
    socket.on('paired', onPaired)

    return () => {
      active = false
      socket.off('pair_dial_progress', onProgress)
      socket.off('paired', onPaired)
      if (code) {
        socket.emit('leave_pair_room', { pair_code: code })
      }
    }
    // We intentionally exclude `code` from deps — including it would
    // re-run the whole start() on every code update.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [puckId, navigate])

  return (
    <main className="flex h-full w-full flex-col items-center justify-center gap-12 px-8 py-16">
      <motion.h1
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }}
        className="font-display text-[clamp(3rem,8vw,7rem)] leading-none tracking-tight text-text"
      >
        DIAL TO START
      </motion.h1>

      {code ? (
        <PairCodeDisplay code={code} progress={progress} />
      ) : error ? (
        <p className="font-body text-2xl text-wrong">{error}</p>
      ) : (
        <p className="font-body text-2xl text-text/60">Requesting code…</p>
      )}

      <motion.p
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="font-body text-xl font-medium text-text/60"
      >
        Hold the puck button for one second, then tilt up/down to dial each digit.
      </motion.p>
    </main>
  )
}
