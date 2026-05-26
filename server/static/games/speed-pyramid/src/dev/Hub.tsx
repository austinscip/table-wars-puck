// PROTOTYPE — Virtual Puck Hub. Sandbox-only route at /dev/hub.
//
// Renders up to 8 Virtual Pucks in a grid, switchable between three
// layout variants via the floating PrototypeSwitcher. Each Virtual
// Puck runs its own state machine + polling loop (see usePuckState.ts)
// and POSTs the same /api/pair/* and /api/sp/* endpoints firmware does.
//
// Lean MVP scope per CONTEXT.md ## Sandbox / dev tooling. No active
// power-up use, no sabotage targeting.
//
// Tree-shaken from prod via VITE_DEV_TOOLS=1 build flag (gated in App.tsx).

import { useEffect, useRef, useState } from 'react'
import PrototypeSwitcher, { useVariant } from './PrototypeSwitcher'
import VariantA from './variants/VariantA'
import VariantB from './variants/VariantB'
import VariantC from './variants/VariantC'

// In-page debug log. The user has no DevTools comfort, so each click +
// each /api/* request appears as a row in a fixed overlay at the bottom.
// Lets us triangulate "I clicked Reset all and nothing happened" without
// asking the user to open Network tabs.
const _debugLines: { ts: number; line: string }[] = []
const _debugSubs = new Set<() => void>()
function debug(line: string) {
  _debugLines.push({ ts: Date.now(), line })
  if (_debugLines.length > 40) _debugLines.shift()
  _debugSubs.forEach((cb) => cb())
}
function useDebugLines() {
  const [, force] = useState(0)
  useEffect(() => {
    const cb = () => force((n) => n + 1)
    _debugSubs.add(cb)
    return () => { _debugSubs.delete(cb) }
  }, [])
  return _debugLines
}
// Monkey-patch fetch once so every request is captured.
let _patched = false
function patchFetch() {
  if (_patched) return
  _patched = true
  const orig = window.fetch.bind(window)
  window.fetch = (input, init) => {
    const url = typeof input === 'string' ? input : (input as Request).url
    const method = (init?.method || 'GET').toUpperCase()
    if (url.startsWith('/api/')) {
      debug(`${method} ${url.split('/api/')[1]}`)
    }
    return orig(input, init).then(
      (r) => {
        if (url.startsWith('/api/')) {
          debug(`-> ${r.status} ${url.split('/api/')[1]}`)
        }
        return r
      },
      (e) => {
        if (url.startsWith('/api/')) debug(`-> ERR ${url.split('/api/')[1]} ${String(e).slice(0, 80)}`)
        throw e
      },
    )
  }
}
patchFetch()

const MAX_PUCKS = 8

interface LobbyMeta {
  code: string | null
  started: boolean
  session_code: string | null
  player_count: number
}

export default function Hub() {
  // Start with two virtual pucks — the most common multi-player test
  // case. User adds more via the "+ Add puck" button.
  const [pucks, setPucks] = useState<number[]>([1, 2])
  const [lobby, setLobby] = useState<LobbyMeta | null>(null)
  const variant = useVariant()

  function addPuck() {
    setPucks((cur) => {
      if (cur.length >= MAX_PUCKS) return cur
      // Pick the lowest unused 1..8 ID.
      for (let id = 1; id <= MAX_PUCKS; id++) {
        if (!cur.includes(id)) return [...cur, id]
      }
      return cur
    })
  }
  function removePuck(id: number) {
    setPucks((cur) => cur.filter((p) => p !== id))
  }

  async function resetAll() {
    debug(`[CLICK] Reset all`)
    try {
      await fetch('/api/pair/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      })
      debug(`[OK] pair/clear`)
    } catch (e) {
      debug(`[ERR] pair/clear ${String(e).slice(0, 60)}`)
    }
    // Re-mount all puck components to reset their internal state.
    const ids = [...pucks]
    setPucks([])
    debug(`[UI] setPucks([]) -> unmount`)
    setTimeout(() => {
      setPucks(ids)
      debug(`[UI] setPucks([${ids.join(',')}]) -> remount`)
    }, 50)
  }

  // Hub-level meta display: poll lobby state for everyone's reference.
  // (The Hub allowed to use polling OR sockets per ADR-0002; polling
  // is fine and matches everything else.)
  useEffect(() => {
    let stop = false
    async function tick() {
      if (stop) return
      try {
        const r = await fetch('/api/pair/lobby-state')
        if (r.ok) {
          const j = (await r.json()) as {
            code: string | null
            started: boolean
            session_code: string | null
            players: Array<unknown>
          }
          if (!stop) {
            setLobby({
              code: j.code,
              started: j.started,
              session_code: j.session_code,
              player_count: j.players?.length ?? 0,
            })
          }
        }
      } catch {
        /* prototype — swallow */
      }
      setTimeout(tick, 1000)
    }
    tick()
    return () => {
      stop = true
    }
  }, [])

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <header className="sticky top-0 z-10 border-b border-white/10 bg-slate-950/95 px-4 py-3 backdrop-blur">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-lg font-bold tracking-tight">
            Virtual Puck Hub <span className="opacity-50">/dev/hub</span>
            <span className="ml-2 rounded bg-yellow-400 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-black">
              build May-26 b866c2d
            </span>
          </h1>
          <button
            className="ml-auto rounded bg-cyan-500/30 px-3 py-1 text-xs hover:bg-cyan-500/50"
            onClick={addPuck}
            disabled={pucks.length >= MAX_PUCKS}
          >
            + Add puck ({pucks.length}/{MAX_PUCKS})
          </button>
          <button
            className="rounded bg-red-500/30 px-3 py-1 text-xs hover:bg-red-500/50"
            onClick={resetAll}
          >
            Reset all
          </button>
          <a
            className="rounded bg-white/10 px-3 py-1 text-xs hover:bg-white/20"
            href="/tv/speed-pyramid/"
            target="_blank"
            rel="noreferrer"
          >
            Open TV ↗
          </a>
        </div>
        <div className="mt-2 flex flex-wrap gap-4 font-mono text-xs opacity-80">
          <span>
            lobby: <span className="text-cyan-300">{lobby?.code ?? '—'}</span>
          </span>
          <span>
            session:{' '}
            <span className="text-cyan-300">
              {lobby?.session_code ?? '—'}
            </span>
          </span>
          <span>
            started:{' '}
            <span className="text-cyan-300">
              {lobby?.started ? 'yes' : 'no'}
            </span>
          </span>
          <span>
            players: <span className="text-cyan-300">{lobby?.player_count ?? 0}</span>
          </span>
        </div>
      </header>

      <main
        className={
          variant === 'A'
            ? 'p-0'
            : variant === 'B'
            ? 'grid gap-4 p-4 [grid-template-columns:repeat(auto-fit,minmax(320px,1fr))]'
            : 'grid gap-3 p-4 [grid-template-columns:repeat(auto-fit,minmax(260px,1fr))]'
        }
      >
        {pucks.map((id) => {
          const onRemove = () => removePuck(id)
          if (variant === 'A')
            return <VariantA key={id} puck_id={id} onRemove={onRemove} />
          if (variant === 'B')
            return <VariantB key={id} puck_id={id} onRemove={onRemove} />
          return <VariantC key={id} puck_id={id} onRemove={onRemove} />
        })}
      </main>

      <PrototypeSwitcher />
      <DebugOverlay />
    </div>
  )
}

function DebugOverlay() {
  const lines = useDebugLines()
  const ref = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [lines.length])
  return (
    <div
      ref={ref}
      className="fixed bottom-12 left-2 right-2 z-20 max-h-40 overflow-y-auto rounded border border-yellow-400/40 bg-black/85 p-2 font-mono text-[10px] leading-tight text-yellow-100"
    >
      <div className="mb-1 font-semibold text-yellow-300">
        DEBUG LOG (latest 40 events) — clear with Reset all
      </div>
      {lines.length === 0 && (
        <div className="opacity-50">No events yet. Click a button.</div>
      )}
      {lines.map((l, i) => (
        <div key={i}>
          <span className="opacity-50">
            {new Date(l.ts).toISOString().slice(11, 19)}
          </span>{' '}
          {l.line}
        </div>
      ))}
    </div>
  )
}
