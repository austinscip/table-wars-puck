// PROTOTYPE — Variant C: Workshop Form.
//
// Structural idea: a vertical label-above-value form. Every piece of
// per-puck state is on screen at once (current state, pending answer,
// pair code, session code, last error). Every possible action listed
// as a separate row. No graphical flair — maximally information-dense.
// Designed for the "I'm debugging a state-machine bug and need to see
// every detail" workflow.

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

function pairCode(s: PuckState): string {
  if ('pair_code' in s && s.pair_code) return s.pair_code
  return '—'
}
function sessionCode(s: PuckState): string {
  if ('session_code' in s && s.session_code) return s.session_code
  return '—'
}
function questionId(s: PuckState): string {
  if (s.kind === 'IN_GAME_ANSWERING' || s.kind === 'IN_GAME_LOCKED')
    return String(s.question_id)
  return '—'
}
function pending(s: PuckState): string {
  if (s.kind === 'IN_GAME_ANSWERING') return s.pending ?? '—'
  if (s.kind === 'IN_GAME_LOCKED') return s.chosen ?? 'TIMEOUT'
  return '—'
}
function isHost(s: PuckState): string {
  if (s.kind === 'LOBBY_WAITING') return s.is_host ? 'yes' : 'no'
  return '—'
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-3 border-b border-white/5 py-1">
      <span className="w-24 shrink-0 font-mono text-[10px] uppercase tracking-wider opacity-60">
        {label}
      </span>
      <span className="font-mono text-xs">{value}</span>
    </div>
  )
}

export default function VariantC({ puck_id, onRemove }: Props) {
  const [hex, name] = PUCK_COLOR_NAMES[puck_id] ?? ['#F8FAFC', 'white']
  const { state, actions } = usePuckState(puck_id)

  return (
    <div className="rounded border border-white/10 bg-slate-950/60 p-3 font-mono">
      <div className="mb-2 flex items-center gap-2">
        <span
          className="inline-block h-3 w-3 rounded-full"
          style={{ background: hex }}
        />
        <span className="text-xs uppercase">
          PUCK #{puck_id} ({name})
        </span>
        {onRemove && (
          <button
            className="ml-auto rounded bg-red-500/20 px-1.5 py-0.5 text-xs hover:bg-red-500/40"
            onClick={onRemove}
          >
            remove
          </button>
        )}
      </div>

      {/* State surface — every field */}
      <Row label="state" value={state.kind} />
      <Row label="pair_code" value={pairCode(state)} />
      <Row label="session" value={sessionCode(state)} />
      <Row label="question_id" value={questionId(state)} />
      <Row label="answer" value={pending(state)} />
      <Row label="is_host" value={isHost(state)} />

      {/* Action rows — explicit list of every command */}
      <div className="mt-3 space-y-1 text-xs">
        <button
          className="block w-full rounded bg-white/5 py-1 text-left text-cyan-300 hover:bg-white/10"
          onClick={actions.hold1s}
        >
          ▸ HOLD_1S
        </button>
        <button
          className="block w-full rounded bg-white/5 py-1 text-left text-cyan-300 hover:bg-white/10"
          onClick={actions.hold3s}
        >
          ▸ HOLD_3S
        </button>
        <button
          className="block w-full rounded bg-white/5 py-1 text-left text-cyan-300 hover:bg-white/10"
          onClick={actions.tap}
        >
          ▸ TAP
        </button>
        {state.kind === 'PAIR_DIALING' && (
          <button
            className="block w-full rounded bg-yellow-400/20 py-1 text-left text-yellow-200 hover:bg-yellow-400/40"
            onClick={actions.confirmCode}
          >
            ▸ CONFIRM_CODE ({state.pair_code})
          </button>
        )}
        {state.kind === 'IN_GAME_ANSWERING' &&
          (['A', 'B', 'C', 'D'] as Letter[]).map((L) => (
            <button
              key={L}
              className={`block w-full rounded py-1 text-left ${
                state.pending === L
                  ? 'bg-yellow-400/30 text-yellow-200'
                  : 'bg-white/5 text-cyan-300 hover:bg-white/10'
              }`}
              onClick={() => actions.lockAnswer(L)}
            >
              ▸ SELECT_ANSWER({L})
            </button>
          ))}
        {state.kind === 'CATEGORY_PICKING' &&
          state.offer.map((c) => (
            <button
              key={c.id}
              className="block w-full rounded bg-white/5 py-1 text-left text-cyan-300 hover:bg-white/10"
              onClick={() => actions.pickCategory(c.id)}
            >
              ▸ PICK_CATEGORY({c.id}, '{c.name}')
            </button>
          ))}
        {state.kind === 'MATCH_ENDED' && (
          <>
            <button
              className="block w-full rounded bg-cyan-400/30 py-1 text-left text-cyan-100 hover:bg-cyan-400/50"
              onClick={actions.tap}
            >
              ▸ PLAY_AGAIN
            </button>
            <button
              className="block w-full rounded bg-white/5 py-1 text-left text-cyan-300 hover:bg-white/10"
              onClick={actions.goBackToStart}
            >
              ▸ BACK_TO_START
            </button>
          </>
        )}
      </div>
    </div>
  )
}
