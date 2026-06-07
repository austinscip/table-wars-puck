import { useEffect, useState } from 'react'

const STORAGE_KEY = 'tw_onboarding_seen'

// Pure gating helpers — testable without a DOM. The overlay shows once per
// browser; a returning player (the TV that's run before) never sees it again.
export function shouldShowOnboarding(storage: Pick<Storage, 'getItem'>): boolean {
  try {
    return storage.getItem(STORAGE_KEY) !== '1'
  } catch {
    return false // private mode / no storage -> don't nag
  }
}

export function markOnboardingSeen(storage: Pick<Storage, 'setItem'>): void {
  try {
    storage.setItem(STORAGE_KEY, '1')
  } catch {
    /* private mode — fine, it just may show again next boot */
  }
}

interface Props {
  /** How long the card stays up before auto-fading (ms). */
  durationMs?: number
}

/**
 * First-time "how to play" card for the unattended bar TV (master-plan Track E,
 * customer self-serve). The pilot is no-staff: a customer walks up cold and has
 * to figure out the puck. Without a hint a first-timer may not realize the puck
 * is tilt-controlled and give up. This shows ONCE (gated by localStorage),
 * auto-dismisses after `durationMs`, and never interrupts a returning player.
 *
 * Self-contained: render <OnboardingOverlay /> inside the question screen and it
 * gates + times itself.
 */
export default function OnboardingOverlay({ durationMs = 6500 }: Props) {
  const [visible, setVisible] = useState(
    () => typeof window !== 'undefined' && shouldShowOnboarding(window.localStorage),
  )
  const [fading, setFading] = useState(false)

  useEffect(() => {
    if (!visible) return
    markOnboardingSeen(window.localStorage)
    // Start the fade a beat before unmount so it eases out, not pops.
    const fadeAt = window.setTimeout(() => setFading(true), Math.max(0, durationMs - 500))
    const hideAt = window.setTimeout(() => setVisible(false), durationMs)
    return () => {
      window.clearTimeout(fadeAt)
      window.clearTimeout(hideAt)
    }
  }, [visible, durationMs])

  if (!visible) return null

  return (
    <div
      aria-hidden
      className={
        'pointer-events-none absolute inset-0 z-40 flex items-center justify-center ' +
        'bg-bg/85 backdrop-blur-sm transition-opacity duration-500 ' +
        (fading ? 'opacity-0' : 'opacity-100')
      }
    >
      <div className="flex flex-col items-center gap-8 rounded-3xl border border-white/10 bg-white/[0.04] px-16 py-12 text-center shadow-2xl">
        <div className="font-display text-[clamp(2rem,5vw,4.5rem)] tracking-wide text-text">
          How to play
        </div>
        <div className="flex items-stretch gap-12">
          <div className="flex flex-col items-center gap-3">
            <div className="text-6xl">🎯</div>
            <div className="font-body text-[clamp(1rem,2vw,1.75rem)] text-text/90">
              <span className="font-semibold text-primary">Tilt</span> your puck to aim
            </div>
          </div>
          <div className="w-px self-stretch bg-white/10" />
          <div className="flex flex-col items-center gap-3">
            <div className="text-6xl">⚡</div>
            <div className="font-body text-[clamp(1rem,2vw,1.75rem)] text-text/90">
              <span className="font-semibold text-accent">Tap</span> the button to lock in
            </div>
          </div>
        </div>
        <div className="font-body text-[clamp(0.85rem,1.5vw,1.25rem)] text-text/50">
          Fastest correct answer wins the round
        </div>
      </div>
    </div>
  )
}
