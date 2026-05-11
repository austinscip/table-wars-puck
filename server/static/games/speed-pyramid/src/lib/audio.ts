/**
 * Speed Pyramid v1 — audio bus.
 *
 * V1 ships procedural Web Audio API tones (no asset files, no AI-
 * generated content, no licenses needed). The PRD specifies CC0
 * sourced MP3s for V2 — see TODO in README. The function names here
 * map 1:1 to the PRD audio asset list so the swap is a body change,
 * not an API change.
 *
 * Honors the user-gesture autoplay restriction: the first `play*` call
 * lazily creates the AudioContext, which requires the document to have
 * received a user gesture (click / keypress). We resume the context
 * automatically when invoked.
 */

let _ctx: AudioContext | null = null
let _unlocked = false

function _create(): AudioContext {
  if (_ctx) return _ctx
  const W = window as unknown as {
    AudioContext: typeof AudioContext
    webkitAudioContext: typeof AudioContext
  }
  const Ctor = W.AudioContext || W.webkitAudioContext
  _ctx = new Ctor()
  return _ctx
}

function ctx(): AudioContext {
  const c = _create()
  if (c.state === 'suspended') void c.resume()
  return c
}

interface ToneOptions {
  freq: number
  durationMs: number
  /** Linear ramp end frequency. If unset, holds at `freq`. */
  endFreq?: number
  /** Peak gain (0-1). Default 0.18 — comfortable across a bar. */
  gain?: number
  type?: OscillatorType
  /** Stagger from caller-relative time (ms). */
  delayMs?: number
}

function tone({
  freq,
  durationMs,
  endFreq,
  gain = 0.18,
  type = 'sine',
  delayMs = 0,
}: ToneOptions) {
  const c = ctx()
  const start = c.currentTime + delayMs / 1000
  const stop = start + durationMs / 1000

  const osc = c.createOscillator()
  osc.type = type
  osc.frequency.setValueAtTime(freq, start)
  if (endFreq !== undefined) {
    osc.frequency.linearRampToValueAtTime(endFreq, stop)
  }

  const g = c.createGain()
  // Quick attack, hold, then short release so we don't click.
  g.gain.setValueAtTime(0, start)
  g.gain.linearRampToValueAtTime(gain, start + 0.005)
  g.gain.setValueAtTime(gain, stop - 0.03)
  g.gain.linearRampToValueAtTime(0, stop)

  osc.connect(g).connect(c.destination)
  osc.start(start)
  osc.stop(stop + 0.02)
}

export const audio = {
  /**
   * MUST be called from a real user-gesture handler (click / touch).
   * Browsers refuse to start an AudioContext otherwise — calling tone()
   * from a Socket.IO event handler creates the context but leaves it
   * 'suspended' silently. Hook this to the first button the user
   * touches (e.g. the demo button or the puck pairing entry).
   */
  unlock() {
    if (_unlocked) return
    const c = _create()
    // resume() returns a Promise — fire-and-forget.
    void c.resume().then(() => {
      _unlocked = true
      // Briefly fire a near-silent tone so iOS / Safari fully unlocks the
      // context (some browsers require an actual audio event during the
      // gesture, not just a resume()).
      tone({ freq: 1, durationMs: 30, gain: 0.0001 })
    })
  },
  /** Soft 800Hz tick — countdown clock in the last 3s. */
  tick() {
    tone({ freq: 880, durationMs: 90, gain: 0.12, type: 'sine' })
  },
  /** Final-second urgent tick — ascending. */
  tickFinal() {
    tone({ freq: 1200, endFreq: 1600, durationMs: 140, gain: 0.18, type: 'triangle' })
  },
  /** Jackbox-style ding-up sweep on answer lock. */
  lockIn() {
    tone({ freq: 700, endFreq: 1500, durationMs: 220, gain: 0.2, type: 'triangle' })
  },
  /** Ascending bell on correct. Two-note arpeggio with second offset. */
  correct() {
    tone({ freq: 880, endFreq: 1320, durationMs: 240, gain: 0.22, type: 'triangle' })
    tone({ freq: 1320, durationMs: 320, gain: 0.18, type: 'sine', delayMs: 200 })
  },
  /** Descending thud on wrong. */
  wrong() {
    tone({ freq: 220, endFreq: 110, durationMs: 380, gain: 0.24, type: 'sawtooth' })
  },
  /** Reveal stinger — short single hit before tier badge. */
  reveal() {
    tone({ freq: 520, durationMs: 120, gain: 0.16, type: 'square' })
  },
  /** Match-end crescendo C4 -> C6, staggered. */
  matchEnd() {
    const notes = [262, 330, 392, 523, 659, 1047]
    notes.forEach((f, i) => {
      tone({ freq: f, durationMs: 240, gain: 0.18, type: 'triangle', delayMs: i * 130 })
    })
  },
  /** Question reveal — overshoot up-stinger when the card lands. */
  questionShow() {
    tone({ freq: 440, endFreq: 660, durationMs: 180, gain: 0.14, type: 'sine' })
  },
}
