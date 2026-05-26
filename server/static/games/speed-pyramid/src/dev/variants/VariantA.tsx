// PROTOTYPE — Variant A: Compact Stacked.
//
// Structural idea: a single horizontal row per puck. Minimal vertical
// footprint — 8 pucks stack tidily on a 1080p screen with room left
// over for the TV preview underneath. State badge inline, action
// buttons inline, no card chrome. Designed for the "I'm running 6
// pucks at once and watching their states race" workflow.

import { usePuckState, type PuckState, type Letter } from '../usePuckState'

const PUCK_COLOR_NAMES: Record<number, [string, string]> = {
  1: ['#3B82F6', 'blue'],
  2: ['#EC4899', 'pink'],
  3: ['#FBBF24', 'gold'],
  4: ['#10B981', 'green'],
  5: ['#A855F7', 'purple'],
  6: ['#F97316', 'orange'],
  7: ['#06B6D4', 'cyan'],
  8: ['#EF4444', 'red'],
}

interface Props {
  puck_id: number
  onRemove?: () => void
}

function describe(s: PuckState): string {
  switch (s.kind) {
    case 'IDLE':
      return 'IDLE'
    case 'PAIR_REQUESTING':
      return '…requesting'
    case 'PAIR_DIALING':
      return `DIALING ${s.pair_code}`
    case 'PAIR_CONFIRMING':
      return '…confirming'
    case 'LOBBY_WAITING':
      return s.session_code
        ? `LOBBY (host=${s.is_host}, started)`
        : `LOBBY (${s.is_host ? 'host' : 'joiner'})`
    case 'IN_GAME_IDLE':
      return 'in-game / idle'
    case 'IN_GAME_ANSWERING':
      return `ANSWERING Q${s.question_id}${s.pending ? ` →${s.pending}` : ''}`
    case 'IN_GAME_LOCKED':
      return `LOCKED Q${s.question_id} →${s.chosen}`
    case 'CATEGORY_PICKING':
      return 'PICK CATEGORY'
    case 'MINIGAME':
      return `MINIGAME ${s.kind_name}`
    case 'MATCH_ENDED':
      return 'MATCH ENDED'
    case 'ERROR':
      return `ERR: ${s.msg}`
  }
}

export default function VariantA({ puck_id, onRemove }: Props) {
  const [hex, name] = PUCK_COLOR_NAMES[puck_id] ?? ['#F8FAFC', 'white']
  const { state, actions } = usePuckState(puck_id)

  return (
    <div
      className="flex flex-wrap items-center gap-2 border-b border-white/10 px-3 py-2 text-sm"
      style={{ borderLeft: `4px solid ${hex}` }}
    >
      <span className="w-16 shrink-0 font-mono text-xs uppercase opacity-70">
        #{puck_id} {name}
      </span>
      <span className="w-44 shrink-0 truncate font-mono text-xs text-cyan-300">
        {describe(state)}
      </span>

      {/* Universal buttons. They're inert in states that don't accept them
          — that's fine for compact mode, the badge says where you are. */}
      <button
        className="rounded bg-white/10 px-2 py-1 text-xs hover:bg-white/20"
        onClick={actions.hold1s}
        disabled={state.kind !== 'IDLE'}
      >
        Hold 1s
      </button>
      <button
        className="rounded bg-white/10 px-2 py-1 text-xs hover:bg-white/20"
        onClick={actions.hold3s}
      >
        Hold 3s
      </button>

      {state.kind === 'PAIR_DIALING' && (
        <button
          className="rounded bg-cyan-500/30 px-2 py-1 text-xs hover:bg-cyan-500/50"
          onClick={actions.confirmCode}
        >
          Confirm {state.pair_code}
        </button>
      )}

      {state.kind === 'LOBBY_WAITING' && state.is_host && !state.session_code && (
        <button
          className="rounded bg-green-500/30 px-2 py-1 text-xs hover:bg-green-500/50"
          onClick={actions.tap}
        >
          Start match
        </button>
      )}

      {state.kind === 'IN_GAME_ANSWERING' &&
        (['A', 'B', 'C', 'D'] as Letter[]).map((L) => (
          <button
            key={L}
            className={`rounded px-2 py-1 text-xs ${
              state.pending === L
                ? 'bg-yellow-400 text-black'
                : 'bg-white/10 hover:bg-white/20'
            }`}
            onClick={() => actions.lockAnswer(L)}
          >
            {L}
          </button>
        ))}

      {state.kind === 'IN_GAME_ANSWERING' && (
        <button
          className="rounded bg-green-500/30 px-2 py-1 text-xs hover:bg-green-500/50"
          onClick={actions.tap}
        >
          Tap (lock)
        </button>
      )}

      {state.kind === 'CATEGORY_PICKING' && (
        <span className="flex gap-1">
          {state.offer.map((c) => (
            <button
              key={c.id}
              className="rounded bg-white/10 px-2 py-1 text-xs hover:bg-white/20"
              onClick={() => actions.pickCategory(c.id)}
              title={c.name}
            >
              {c.emoji} {c.name.slice(0, 14)}
            </button>
          ))}
        </span>
      )}

      {state.kind === 'MINIGAME' && (
        <button
          className="rounded bg-orange-400/30 px-2 py-1 text-xs hover:bg-orange-400/50"
          onClick={actions.tap}
        >
          Fire
        </button>
      )}

      {state.kind === 'MATCH_ENDED' && (
        <>
          <button
            className="rounded bg-cyan-400/30 px-2 py-1 text-xs hover:bg-cyan-400/50"
            onClick={actions.tap}
          >
            Play again
          </button>
          <button
            className="rounded bg-white/10 px-2 py-1 text-xs hover:bg-white/20"
            onClick={actions.goBackToStart}
            title="Clear the lobby + return the TV to title"
          >
            Back to start
          </button>
        </>
      )}

      {onRemove && (
        <button
          className="ml-auto rounded bg-red-500/20 px-2 py-1 text-xs hover:bg-red-500/40"
          onClick={onRemove}
        >
          ×
        </button>
      )}
    </div>
  )
}
