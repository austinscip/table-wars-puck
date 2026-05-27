import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { api, type LobbyPlayer } from '../lib/api'
import { getSocket } from '../lib/socket'
import { audio } from '../lib/audio'

interface PlayerJoinedEvent {
  puck_id: number
  color: string
  color_name: string
  role: 'host' | 'joiner'
  players: LobbyPlayer[]
}

interface MatchStartedEvent {
  session_code: string
  host_puck_id: number
  players: LobbyPlayer[]
}

interface PlayerLeftEvent {
  puck_id: number
  players: LobbyPlayer[]
}

interface LobbyCancelledEvent {
  by_puck_id: number
  reason: string
}

/**
 * Lobby screen — what's on the TV between "first puck paired" and
 * "host taps start". Shows:
 *   - The shared pair code (so additional pucks can join by dialing it)
 *   - A strip of joined-players avatars (color-coded by puck_id)
 *   - A "Hold your puck button to join" hint for any non-joined puck
 *   - A "Player 1: tap your puck to start" hint for the host
 *
 * Subscribes to 'player_joined' and 'match_started' socket events.
 * Navigates to /countdown/:session_code on 'match_started'.
 */
export default function LobbyScreen() {
  const navigate = useNavigate()
  const { lobbyCode } = useParams<{ lobbyCode: string }>()
  const [params] = useSearchParams()
  const isDemo = params.get('demo') === '1'
  const puckId = params.get('puck_id') ?? '1'

  const [players, setPlayers] = useState<LobbyPlayer[]>([])
  const [hostPuckId, setHostPuckId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!lobbyCode) return
    const socket = getSocket()
    socket.emit('join_pair_room', { pair_code: lobbyCode })

    api.pair
      .lobbyState()
      .then((state) => {
        if (!state.active) {
          setError('Lobby expired or was cleared.')
          return
        }
        setPlayers(state.players ?? [])
        setHostPuckId(state.host_puck_id ?? null)
        // If the match already started before we mounted (e.g. we
        // refreshed mid-countdown), jump there directly.
        if (state.started && state.session_code) {
          const qs = isDemo ? `?demo=1&puck_id=${puckId}` : ''
          navigate(`/countdown/${state.session_code}${qs}`, { replace: true })
        }
      })
      .catch((e) => setError((e as Error).message))

    function onPlayerJoined(p: PlayerJoinedEvent) {
      // R016: cue each new puck joining the lobby.
      audio.joined()
      setPlayers(p.players)
    }
    function onMatchStarted(p: MatchStartedEvent) {
      const qs = isDemo ? `?demo=1&puck_id=${puckId}` : ''
      navigate(`/countdown/${p.session_code}${qs}`)
    }
    function onPlayerLeft(p: PlayerLeftEvent) {
      setPlayers(p.players)
    }
    function onLobbyCancelled(_p: LobbyCancelledEvent) {
      // Host bailed — kick everyone back to title.
      navigate('/', { replace: true })
    }

    socket.on('player_joined', onPlayerJoined)
    socket.on('match_started', onMatchStarted)
    socket.on('player_left', onPlayerLeft)
    socket.on('lobby_cancelled', onLobbyCancelled)

    return () => {
      socket.off('player_joined', onPlayerJoined)
      socket.off('match_started', onMatchStarted)
      socket.off('player_left', onPlayerLeft)
      socket.off('lobby_cancelled', onLobbyCancelled)
    }
  }, [lobbyCode, navigate, isDemo, puckId])

  // Demo-mode: auto-tap "start" 1.5s after the lobby loads, simulating
  // the host pressing the button. Single-puck demo flow only.
  useEffect(() => {
    if (!isDemo || players.length === 0) return
    const hostId = hostPuckId
    if (hostId === null) return
    const t = window.setTimeout(() => {
      void api.pair.start(hostId).catch(() => {})
    }, 1500)
    return () => window.clearTimeout(t)
  }, [isDemo, players.length, hostPuckId])

  return (
    <main className="flex h-full w-full flex-col items-center justify-center gap-12 px-8 py-12">
      <motion.h1
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }}
        className="font-display text-[clamp(3rem,8vw,7rem)] leading-none tracking-tight text-text"
      >
        LOBBY
      </motion.h1>

      {/* Shared pair code — kept visible so additional pucks can join. */}
      <div className="flex flex-col items-center gap-3">
        <span className="font-body text-base font-medium uppercase tracking-widest text-text/40">
          Code to join
        </span>
        <div className="font-mono text-[clamp(3rem,7vw,8rem)] font-bold leading-none tracking-widest text-text">
          {lobbyCode}
        </div>
      </div>

      {/* Joined players strip */}
      <div className="flex flex-col items-center gap-3">
        <span className="font-body text-base font-medium uppercase tracking-widest text-text/40">
          {players.length === 0
            ? 'Waiting for first player…'
            : `${players.length} player${players.length === 1 ? '' : 's'} joined`}
        </span>
        <div className="flex flex-row flex-wrap items-center justify-center gap-4 md:gap-6">
          <AnimatePresence>
            {players.map((p) => (
              <motion.div
                key={p.puck_id}
                initial={{ scale: 0.4, opacity: 0, y: 20 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                exit={{ scale: 0.4, opacity: 0, y: -20 }}
                transition={{
                  duration: 0.45,
                  ease: [0.34, 1.56, 0.64, 1],
                }}
                className="flex flex-col items-center gap-2"
              >
                <div
                  className="flex h-[clamp(4rem,8vw,8rem)] w-[clamp(4rem,8vw,8rem)] items-center justify-center rounded-full font-display text-[clamp(2rem,4vw,4rem)] text-text"
                  style={{ backgroundColor: p.color }}
                >
                  {p.puck_id}
                </div>
                <span className="font-body text-base font-medium text-text/70">
                  {p.is_host ? `Puck ${p.puck_id} · HOST` : `Puck ${p.puck_id}`}
                </span>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Host start hint */}
      {players.length > 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.4 }}
          className="flex flex-col items-center gap-2 font-body text-xl"
        >
          <span className="text-text/70">
            Host (
            <span className="font-bold text-primary">Puck {hostPuckId}</span>
            ): tap your puck to start
          </span>
          <span className="text-text/40">
            Other players: hold your puck button for 1 second to join
          </span>
        </motion.div>
      ) : null}

      {error ? (
        <p className="font-body text-2xl text-wrong">{error}</p>
      ) : null}
    </main>
  )
}
