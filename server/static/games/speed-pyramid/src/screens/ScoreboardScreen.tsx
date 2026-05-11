import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api, type FinalResults } from '../lib/api'
import { getSocket } from '../lib/socket'
import { audio } from '../lib/audio'
import CountUpScore from '../components/CountUpScore'

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
    socket.on('match_reset', onReset)
    return () => {
      socket.off('match_reset', onReset)
    }
  }, [sessionCode, navigate])

  return (
    <main className="flex h-full w-full flex-col items-center justify-center gap-12 px-12 py-12">
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
        <div className="flex w-full max-w-5xl flex-col gap-6">
          {results.players.length === 0 ? (
            <p className="font-body text-2xl text-text/60">
              No answers recorded.
            </p>
          ) : (
            results.players
              .slice()
              .sort((a, b) => b.total - a.total)
              .map((p, i) => (
                <motion.div
                  key={p.puck_id}
                  initial={{ y: 30, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{
                    duration: 0.45,
                    delay: 0.15 * i,
                    ease: [0.34, 1.56, 0.64, 1],
                  }}
                  className="flex items-center justify-between rounded-3xl border-2 border-text/10 bg-text/5 px-8 py-6"
                >
                  <div className="flex flex-col">
                    <span
                      className={`font-display text-[clamp(2rem,5vw,4.5rem)] leading-none ${
                        TIER_COLOR[p.tier] ?? 'text-text'
                      }`}
                    >
                      {p.tier}
                    </span>
                    <span className="font-body text-xl text-text/60">
                      Puck #{p.puck_id} · {p.correct}/{p.answered} correct
                    </span>
                  </div>
                  <CountUpScore
                    to={p.total}
                    durationMs={1400}
                    delayMs={400 + i * 200}
                    className="font-mono text-[clamp(3rem,7vw,6.5rem)] font-bold leading-none text-text"
                  />
                </motion.div>
              ))
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
