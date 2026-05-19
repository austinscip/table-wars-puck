// PROTOTYPE — Variant B: Game Controller card.
//
// Structural idea: each puck rendered as a chunky faux-controller — a
// D-pad on the left, four ABXY-style face buttons on the right, state
// LED across the top, "Hold" + "Tap" pills along the bottom. Mimics
// holding the real ESP32 puck. Bigger per-puck footprint but reads at
// a glance and feels game-y. Designed for the "I'm pretending to play"
// solo workflow.

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

function shortState(s: PuckState): string {
  switch (s.kind) {
    case 'IDLE':
      return 'idle'
    case 'PAIR_REQUESTING':
      return 'requesting'
    case 'PAIR_DIALING':
      return `dial ${s.pair_code}`
    case 'PAIR_CONFIRMING':
      return 'confirming'
    case 'LOBBY_WAITING':
      return s.session_code ? 'lobby (started)' : 'lobby'
    case 'IN_GAME_IDLE':
      return 'waiting Q'
    case 'IN_GAME_ANSWERING':
      return `Q${s.question_id}`
    case 'IN_GAME_LOCKED':
      return `locked ${s.chosen}`
    case 'CATEGORY_PICKING':
      return 'pick category'
    case 'MINIGAME':
      return `mg/${s.kind_name}`
    case 'MATCH_ENDED':
      return 'match end'
    case 'ERROR':
      return 'error'
  }
}

export default function VariantB({ puck_id, onRemove }: Props) {
  const [hex, name] = PUCK_COLOR_NAMES[puck_id] ?? ['#F8FAFC', 'white']
  const { state, actions } = usePuckState(puck_id)

  const tiltActive = state.kind === 'IN_GAME_ANSWERING'
  const pending = state.kind === 'IN_GAME_ANSWERING' ? state.pending : undefined

  return (
    <div
      className="relative flex flex-col rounded-2xl bg-slate-900/80 p-4 shadow-lg ring-1 ring-white/10"
      style={{ minWidth: 320 }}
    >
      {/* State LED bar */}
      <div className="mb-3 flex items-center gap-3">
        <div
          className="h-3 w-3 rounded-full"
          style={{ background: hex, boxShadow: `0 0 8px ${hex}` }}
        />
        <span className="font-mono text-xs uppercase tracking-wide opacity-80">
          puck #{puck_id} · {name}
        </span>
        <span className="ml-auto rounded bg-white/5 px-2 py-0.5 font-mono text-[11px] text-cyan-300">
          {shortState(state)}
        </span>
        {onRemove && (
          <button
            className="rounded bg-red-500/20 px-1.5 py-0.5 text-xs hover:bg-red-500/40"
            onClick={onRemove}
          >
            ×
          </button>
        )}
      </div>

      {/* Controller body */}
      <div className="flex items-start justify-between gap-4">
        {/* D-pad (left) — directional tilt */}
        <div className="grid grid-cols-3 grid-rows-3 gap-1">
          <span />
          <button
            className={`rounded-md py-2 text-xs ${
              tiltActive && pending === 'A'
                ? 'bg-yellow-400 text-black'
                : 'bg-white/10 hover:bg-white/20'
            }`}
            onClick={() => actions.tilt('N')}
            disabled={!tiltActive}
          >
            ▲
          </button>
          <span />
          <button
            className={`rounded-md py-2 text-xs ${
              tiltActive && pending === 'D'
                ? 'bg-yellow-400 text-black'
                : 'bg-white/10 hover:bg-white/20'
            }`}
            onClick={() => actions.tilt('W')}
            disabled={!tiltActive}
          >
            ◀
          </button>
          <span />
          <button
            className={`rounded-md py-2 text-xs ${
              tiltActive && pending === 'B'
                ? 'bg-yellow-400 text-black'
                : 'bg-white/10 hover:bg-white/20'
            }`}
            onClick={() => actions.tilt('E')}
            disabled={!tiltActive}
          >
            ▶
          </button>
          <span />
          <button
            className={`rounded-md py-2 text-xs ${
              tiltActive && pending === 'C'
                ? 'bg-yellow-400 text-black'
                : 'bg-white/10 hover:bg-white/20'
            }`}
            onClick={() => actions.tilt('S')}
            disabled={!tiltActive}
          >
            ▼
          </button>
          <span />
        </div>

        {/* Face buttons (right) — A/B/C/D when answering */}
        <div className="grid grid-cols-2 gap-2">
          {(['A', 'B', 'C', 'D'] as Letter[]).map((L) => (
            <button
              key={L}
              className={`h-14 w-14 rounded-full text-base font-bold ${
                tiltActive
                  ? pending === L
                    ? 'bg-yellow-400 text-black'
                    : 'bg-white/10 hover:bg-white/20'
                  : 'bg-white/5 opacity-50'
              }`}
              onClick={async () => { actions.selectAnswer(L); await actions.tap() }}
              disabled={!tiltActive}
            >
              {L}
            </button>
          ))}
        </div>
      </div>

      {/* Bottom action row */}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          className="rounded bg-white/10 px-3 py-1.5 text-xs hover:bg-white/20"
          onClick={actions.hold1s}
          disabled={state.kind !== 'IDLE'}
        >
          Hold 1s
        </button>
        <button
          className="rounded bg-white/10 px-3 py-1.5 text-xs hover:bg-white/20"
          onClick={actions.hold3s}
        >
          Hold 3s
        </button>
        <button
          className="rounded bg-cyan-400/30 px-3 py-1.5 text-xs hover:bg-cyan-400/50"
          onClick={actions.tap}
        >
          TAP
        </button>
        {state.kind === 'PAIR_DIALING' && (
          <button
            className="rounded bg-yellow-400 px-3 py-1.5 text-xs font-semibold text-black hover:bg-yellow-300"
            onClick={actions.confirmCode}
          >
            Confirm {state.pair_code}
          </button>
        )}
      </div>

      {/* Inline category picker when applicable */}
      {state.kind === 'CATEGORY_PICKING' && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {state.offer.map((c) => (
            <button
              key={c.id}
              className="rounded bg-white/10 px-2 py-1 text-xs hover:bg-white/20"
              onClick={() => actions.pickCategory(c.id)}
            >
              {c.emoji} {c.name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
