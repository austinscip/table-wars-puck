// PROTOTYPE — floating bottom-center variant switcher. Cycles A → B → C
// via arrows or ←/→ keys. Hidden in production builds.

import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'

const VARIANTS = ['A', 'B', 'C'] as const
type Variant = (typeof VARIANTS)[number]
const NAMES: Record<Variant, string> = {
  A: 'Compact stacked',
  B: 'Game controller',
  C: 'Workshop form',
}

export function useVariant(): Variant {
  const [params] = useSearchParams()
  const raw = params.get('variant') ?? 'A'
  return (VARIANTS as readonly string[]).includes(raw) ? (raw as Variant) : 'A'
}

export default function PrototypeSwitcher() {
  const [params, setParams] = useSearchParams()
  const current = useVariant()

  function cycle(delta: 1 | -1) {
    const i = VARIANTS.indexOf(current)
    const next = VARIANTS[(i + delta + VARIANTS.length) % VARIANTS.length]
    const np = new URLSearchParams(params)
    np.set('variant', next)
    setParams(np, { replace: true })
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const t = e.target as HTMLElement | null
      const isInput =
        t &&
        (t.tagName === 'INPUT' ||
          t.tagName === 'TEXTAREA' ||
          t.isContentEditable)
      if (isInput) return
      if (e.key === 'ArrowRight') cycle(1)
      if (e.key === 'ArrowLeft') cycle(-1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  // Don't render in prod even if somehow mounted.
  if (import.meta.env.PROD) return null

  return (
    <div className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-full bg-black/80 px-3 py-1.5 shadow-lg ring-1 ring-white/20 backdrop-blur">
      <button
        className="rounded-full bg-white/10 px-2 py-0.5 hover:bg-white/20"
        onClick={() => cycle(-1)}
        aria-label="Previous variant"
      >
        ←
      </button>
      <span className="font-mono text-xs uppercase">
        {current} — {NAMES[current]}
      </span>
      <button
        className="rounded-full bg-white/10 px-2 py-0.5 hover:bg-white/20"
        onClick={() => cycle(1)}
        aria-label="Next variant"
      >
        →
      </button>
    </div>
  )
}
