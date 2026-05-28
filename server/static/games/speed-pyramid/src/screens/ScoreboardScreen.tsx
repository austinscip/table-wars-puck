import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api, type FinalResults } from '../lib/api'
import { getSocket } from '../lib/socket'
import { audio } from '../lib/audio'
import CountUpScore from '../components/CountUpScore'
import AmbientBackground from '../components/AmbientBackground'

const TIER_COLOR: Record<string, string> = {
  LEGENDARY: 'text-correct',
  EXPERT: 'text-primary',
  AVERAGE: 'text-accent',
  TIMEOUT: 'text-text/40',
  WRONG: 'text-wrong',
  NONE: 'text-text/40',
}

/**
 * Scoreboard reveal — fired after match_ended (or when the user lands
 * here directly via deep link). Loads final results from the server and
 * staggers a count-up animation per player. Listens for `match_reset`
 * to navigate back to /question/:code when the puck taps Play Again.
 */
export default function ScoreboardScreen() {
  const navigate = useNavigate()
  const { sessionCode } = useParams<{ sessionCode: string }>()
  const [results, setResults] = useState<FinalResults | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionCode) return
    const socket = getSocket()
    socket.emit('join_session_room', { session_code: sessionCode })

    api.sp
      .finalResults(sessionCode)
      .then((r) => {
        setResults(r)
        // Match-end crescendo plays in sync with the count-up entrance.
        window.setTimeout(() => audio.matchEnd(), 250)
      })
      .catch((e) => setError((e as Error).message))

    function onReset() {
      navigate(`/question/${sessionCode}`)
    }
    function onLobbyCancelled() {
      // Hub Reset all or per-puck "Back to start" cleared the lobby.
      // Don't stay on a scoreboard tied to a session that no longer
      // exists — bounce to title so the next pair flow can start fresh.
      navigate('/', { replace: true })
    }
    socket.on('match_reset', onReset)
    socket.on('lobby_cancelled', onLobbyCancelled)
    return () => {
      socket.off('match_reset', onReset)
      socket.off('lobby_cancelled', onLobbyCancelled)
    }
  }, [sessionCode, navigate])

  // UX-10: a bar kiosk must not park on a finished match forever. If no
  // puck Play-Again (match_reset) or Reset (lobby_cancelled) arrives, the
  // listeners above never fire. Self-navigate back to the title after 30s
  // of inactivity so the attract loop resumes. Cleared on unmount (which
  // also covers the case where match_reset / lobby_cancelled navigated away
  // first, since that re-renders this screen out).
  useEffect(() => {
    const timer = window.setTimeout(() => {
      navigate('/', { replace: true })
    }, 30000)
    return () => window.clearTimeout(timer)
  }, [navigate])

  return (
    <main className="relative flex h-full w-full flex-col items-center justify-center gap-12 overflow-hidden px-12 py-12">
      <AmbientBackground glowA="rgba(251,191,36,0.22)" glowB="rgba(16,185,129,0.16)" />
      <motion.h1
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }}
        className="font-display text-[clamp(4rem,11vw,11rem)] leading-none tracking-tight text-correct"
      >
        MATCH COMPLETE
      </motion.h1>

      {error ? (
        <p className="font-body text-2xl text-wrong">{error}</p>
      ) : !results ? (
        <p className="font-body text-2xl text-text/60">Tallying scores…</p>
      ) : (
        <div
          className={
            results.players.length > 4
              ? 'grid w-full max-w-6xl grid-cols-2 gap-4'
              : 'flex w-full max-w-5xl flex-col gap-6'
          }
        >
          {results.players.length === 0 ? (
            <p className="font-body text-2xl text-text/60">
              No answers recorded.
            </p>
          ) : (
            results.players
              .slice()
              // R040: trust the server's deterministic standing (rank +
              // is_winner apply points -> faster aggregate response ->
              // lowest puck_id). Fall back to total-only ordering with a
              // response-time tie-break only when an older server omits rank.
              .sort((a, b) => {
                if (a.rank != null && b.rank != null) return a.rank - b.rank
                if (b.total !== a.total) return b.total - a.total
                return (
                  (a.sum_response_time_ms ?? 0) - (b.sum_response_time_ms ?? 0) ||
                  a.puck_id - b.puck_id
                )
              })
              .map((p, i) => {
                const isWinner =
                  p.is_winner != null ? p.is_winner : i === 0 && p.total > 0
                const compact = results.players.length > 4
                return (
                  <motion.div
                    key={p.puck_id}
                    initial={{ y: 30, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{
                      duration: 0.45,
                      delay: 0.15 * i,
                      ease: [0.34, 1.56, 0.64, 1],
                    }}
                    className={`flex items-center rounded-3xl border-2 ${
                      isWinner ? 'border-correct' : 'border-text/10'
                    } bg-text/5 ${compact ? 'gap-3 px-4 py-3' : 'gap-6 px-8 py-6'}`}
                    style={
                      isWinner
                        ? { boxShadow: '0 0 60px rgba(251,191,36,0.5)' }
                        : undefined
                    }
                  >
                    <div
                      className={`flex flex-none items-center justify-center rounded-full font-display ${
                        compact
                          ? 'h-[clamp(2.5rem,4vw,4rem)] w-[clamp(2.5rem,4vw,4rem)] text-[clamp(1.25rem,2vw,2rem)]'
                          : 'h-[clamp(4rem,7vw,7rem)] w-[clamp(4rem,7vw,7rem)] text-[clamp(2rem,3.5vw,3.5rem)]'
                      }`}
                      style={{
                        backgroundColor: p.color ?? '#F8FAFC',
                        color: '#0A0E1A',
                      }}
                    >
                      {p.puck_id}
                    </div>
                    <div className="flex flex-1 flex-col overflow-hidden">
                      <span
                        className={`truncate font-display leading-none ${
                          TIER_COLOR[p.tier] ?? 'text-text'
                        } ${compact ? 'text-[clamp(1.25rem,2.5vw,2.5rem)]' : 'text-[clamp(2rem,5vw,4.5rem)]'}`}
                      >
                        {isWinner ? '👑 ' : ''}
                        {p.tier}
                      </span>
                      <span className={`font-body text-text/60 ${compact ? 'text-sm' : 'text-xl'}`}>
                        Puck #{p.puck_id} · {p.correct}/{results.total_rounds} correct
                      </span>
                    </div>
                    <CountUpScore
                      to={p.total}
                      durationMs={1400}
                      delayMs={400 + i * 200}
                      className={`font-mono font-bold leading-none text-text ${
                        compact
                          ? 'text-[clamp(1.5rem,3vw,3.5rem)]'
                          : 'text-[clamp(3rem,7vw,6.5rem)]'
                      }`}
                    />
                  </motion.div>
                )
              })
          )}
        </div>
      )}

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2.5, duration: 0.6 }}
        className="flex flex-col items-center gap-2 font-body text-xl text-text/60"
      >
        <span>
          <span className="text-primary">Tap</span> the puck to Play Again
        </span>
        <span>
          <span className="text-accent">Hold</span> the puck to switch players
        </span>
      </motion.div>
    </main>
  )
}
