import { useEffect, useRef, useState } from 'react'
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

interface DialPreviewEvent {
  puck_id: number
  digit_index: number
  digit: number
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
  const isDemo = params.get('demo') === '1'

  const [code, setCode] = useState<string | null>(null)
  const [progress, setProgress] = useState<(number | null)[]>(
    () => Array(6).fill(null) as (number | null)[],
  )
  const [previewDigit, setPreviewDigit] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const demoStartedRef = useRef(false)

  // Active slot = first index in `progress` that's still null. Once
  // all 6 are filled this is 6, but at that point the server should
  // have emitted `paired` and we're navigating away.
  const activeSlot = (() => {
    const idx = progress.findIndex((d) => d === null || d === undefined)
    return idx < 0 ? 6 : idx
  })()

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
      setPreviewDigit(null)  // locked, clear in-flight preview
    }
    function onPreview(payload: DialPreviewEvent) {
      if (payload.puck_id !== puckId) return
      setPreviewDigit(payload.digit)
    }
    function onPaired(payload: PairedEvent) {
      if (payload.puck_id !== puckId) return
      const qs = isDemo ? `?demo=1&puck_id=${puckId}` : ''
      navigate(`/countdown/${payload.session_code}${qs}`)
    }

    socket.on('pair_dial_progress', onProgress)
    socket.on('pair_dial_preview', onPreview)
    socket.on('paired', onPaired)

    return () => {
      active = false
      socket.off('pair_dial_progress', onProgress)
      socket.off('pair_dial_preview', onPreview)
      socket.off('paired', onPaired)
      if (code) {
        socket.emit('leave_pair_room', { pair_code: code })
      }
    }
    // We intentionally exclude `code` from deps — including it would
    // re-run the whole start() on every code update.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [puckId, navigate])

  // Demo-mode: auto-dial the code shown on the TV. Lets a laptop run
  // the full match without a real puck. Triggered once per session.
  useEffect(() => {
    if (!isDemo || !code || demoStartedRef.current) return
    demoStartedRef.current = true
    let cancelled = false

    async function autoDial(c: string) {
      // Small lead-in so the user sees the code render before slots
      // start filling.
      await new Promise((r) => window.setTimeout(r, 700))
      for (let i = 0; i < 6; i++) {
        if (cancelled) return
        const digit = Number(c[i])
        try {
          await api.pair.dial(puckId, i, digit)
        } catch {
          /* live mirror is best-effort; server still validates on confirm */
        }
        await new Promise((r) => window.setTimeout(r, 900))
      }
      if (cancelled) return
      try {
        await api.pair.confirm(puckId, c)
        // 'paired' socket event handles the navigation.
      } catch (e) {
        setError((e as Error).message)
      }
    }

    void autoDial(code)

    return () => {
      cancelled = true
    }
  }, [isDemo, code, puckId])

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
        <PairCodeDisplay
          code={code}
          progress={progress}
          activeSlot={activeSlot}
          previewDigit={previewDigit}
        />
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
