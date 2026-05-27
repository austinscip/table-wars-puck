import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api, type LobbyPlayer } from '../lib/api'
import { getSocket } from '../lib/socket'
import PairCodeDisplay from '../components/PairCodeDisplay'
import { audio } from '../lib/audio'

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

interface PlayerJoinedEvent {
  puck_id: number
  color: string
  color_name: string
  role: 'host' | 'joiner'
  players: LobbyPlayer[]
}

/**
 * Pair screen — v2 flow.
 *
 * For PLAYER 1 (host): full live mirror of their dial as they enter the
 * 6-digit code on the puck. Navigates to /lobby/:code after a
 * 'player_joined' event for this puck_id arrives (= they finished their
 * dial successfully).
 *
 * For PLAYER 2+ (joiner): this screen is rarely seen because the title
 * page auto-advances on the FIRST puck's pair request, then the TV is
 * already on /lobby/:code. The PairScreen still handles the joiner case
 * defensively: shows the code + a 'waiting for your dial' panel without
 * the live mirror.
 */
export default function PairScreen() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const puckId = Number(params.get('puck_id') ?? '1')
  const isDemo = params.get('demo') === '1'

  const [code, setCode] = useState<string | null>(null)
  const codeRef = useRef<string | null>(null)
  const [role, setRole] = useState<'host' | 'joiner' | null>(null)
  const [progress, setProgress] = useState<(number | null)[]>(
    () => Array(6).fill(null) as (number | null)[],
  )
  const [previewDigit, setPreviewDigit] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const demoStartedRef = useRef(false)

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
        codeRef.current = res.pair_code
        setCode(res.pair_code)
        setRole(res.role)
        socket.emit('join_pair_room', { pair_code: res.pair_code })
      } catch (e) {
        if (!active) return
        setError((e as Error).message)
      }
    }
    start()

    function onProgress(payload: DialProgressEvent) {
      if (payload.puck_id !== puckId) return
      // R015: each locked digit gets a confirmation blip.
      audio.digitLock()
      setProgress(payload.progress)
      setPreviewDigit(null)
    }
    function onPreview(payload: DialPreviewEvent) {
      if (payload.puck_id !== puckId) return
      setPreviewDigit(payload.digit)
    }
    function onPlayerJoined(payload: PlayerJoinedEvent) {
      // Read code from ref because this closure was created before setCode ran.
      const c = codeRef.current
      if (payload.puck_id === puckId && c) {
        // R015: full pair confirmation cue once all 6 digits land and
        // the host transitions to lobby.
        audio.joined()
        const qs = isDemo ? `?demo=1&puck_id=${puckId}` : ''
        navigate(`/lobby/${c}${qs}`)
      }
    }

    socket.on('pair_dial_progress', onProgress)
    socket.on('pair_dial_preview', onPreview)
    socket.on('player_joined', onPlayerJoined)

    return () => {
      active = false
      socket.off('pair_dial_progress', onProgress)
      socket.off('pair_dial_preview', onPreview)
      socket.off('player_joined', onPlayerJoined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [puckId, navigate])

  // Demo-mode auto-dial — only for the host (the demo flow is single-puck).
  useEffect(() => {
    if (!isDemo || !code || role !== 'host' || demoStartedRef.current) return
    demoStartedRef.current = true
    let cancelled = false
    async function autoDial(c: string) {
      await new Promise((r) => window.setTimeout(r, 700))
      for (let i = 0; i < 6; i++) {
        if (cancelled) return
        const digit = Number(c[i])
        try { await api.pair.dial(puckId, i, digit) } catch {}
        await new Promise((r) => window.setTimeout(r, 900))
      }
      if (cancelled) return
      try { await api.pair.confirm(puckId, c) } catch (e) {
        setError((e as Error).message)
      }
    }
    void autoDial(code)
    return () => { cancelled = true }
  }, [isDemo, code, role, puckId])

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
        role === 'joiner' ? (
          // Joiner: no live mirror, just the code and a hint.
          <div className="flex flex-col items-center gap-6">
            <div className="font-mono text-[clamp(4rem,9vw,11rem)] font-bold leading-none text-text">
              {code}
            </div>
            <p className="font-body text-2xl text-text/60">
              Dial these 6 digits on your puck.
            </p>
          </div>
        ) : (
          <PairCodeDisplay
            code={code}
            progress={progress}
            activeSlot={activeSlot}
            previewDigit={previewDigit}
          />
        )
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
