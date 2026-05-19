/**
 * Speed Pyramid v1 — audio bus.
 *
 * Two layers, in order of priority:
 *
 *   1. **Sample layer.** If a CC0 MP3 exists at the expected URL for an
 *      event (e.g. `/assets/audio/sfx_lock.mp3`), play it. This is the
 *      production audio path — see `docs/assets/LICENSES.md` for the
 *      asset shopping list. We use plain `HTMLAudioElement` rather
 *      than Howler.js because we already have a Web Audio context for
 *      the procedural layer and don't need another runtime.
 *
 *   2. **Procedural layer (fallback).** Multi-oscillator chords with
 *      ADSR envelopes via Web Audio. Plays when the MP3 file is missing
 *      or fails to load — so the bar always hears *something*.
 *
 * Audio unlocks on the first user gesture (handled by `AudioPrimer` in
 * `App.tsx`). Both layers stay silent until then.
 */

const AUDIO_BASE = '/tv/speed-pyramid/assets/audio'

// ---------- Sample layer ----------

const _samples = new Map<string, HTMLAudioElement>()
const _sampleStatus = new Map<string, 'unknown' | 'present' | 'missing'>()

function _sample(name: string): HTMLAudioElement | null {
  const status = _sampleStatus.get(name)
  if (status === 'missing') return null

  let el = _samples.get(name)
  if (!el) {
    el = new Audio(`${AUDIO_BASE}/${name}.mp3`)
    el.preload = 'auto'
    el.addEventListener('error', () => {
      _sampleStatus.set(name, 'missing')
    })
    el.addEventListener('canplaythrough', () => {
      _sampleStatus.set(name, 'present')
    })
    _samples.set(name, el)
    _sampleStatus.set(name, 'unknown')
  }
  return el
}

function _playSample(name: string): boolean {
  // Side-effect: create the element so its 'canplaythrough'/'error'
  // listeners can flip status. The first call always returns false
  // (status is 'unknown') so the procedural fallback fires — otherwise
  // Q1 is silent: play() resolves synchronously, .catch() runs later
  // and sets 'missing', but by then _play has already skipped the
  // fallback. Q2 then sees 'missing' and falls through to procedural,
  // which is why the user heard sound on Q2-Q7 but not Q1.
  const el = _sample(name)
  if (!el) return false
  if (_sampleStatus.get(name) !== 'present') return false
  try {
    el.currentTime = 0
    void el.play().catch(() => {
      _sampleStatus.set(name, 'missing')
    })
    return true
  } catch {
    return false
  }
}

// ---------- Procedural layer ----------

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

interface VoiceOptions {
  freq: number
  /** Total note duration in ms. */
  durationMs: number
  /** Optional linear pitch ramp end. */
  endFreq?: number
  /** Peak gain after attack (0-1). */
  peak?: number
  /** Wave shape. */
  type?: OscillatorType
  /** Stagger from now (ms). */
  delayMs?: number
  /** Detune in cents — handy for stacking unison voices. */
  detuneCents?: number
}

function _voice({
  freq,
  durationMs,
  endFreq,
  peak = 0.18,
  type = 'sine',
  delayMs = 0,
  detuneCents = 0,
}: VoiceOptions) {
  const c = ctx()
  const start = c.currentTime + delayMs / 1000
  const dur = durationMs / 1000

  const osc = c.createOscillator()
  osc.type = type
  osc.frequency.setValueAtTime(freq, start)
  if (endFreq !== undefined) {
    osc.frequency.linearRampToValueAtTime(endFreq, start + dur)
  }
  if (detuneCents !== 0) {
    osc.detune.setValueAtTime(detuneCents, start)
  }

  // ADSR-ish: short attack, sustain, longer release.
  const attack = Math.min(0.015, dur * 0.2)
  const release = Math.min(0.12, dur * 0.5)
  const sustainEnd = start + dur - release

  const g = c.createGain()
  g.gain.setValueAtTime(0, start)
  g.gain.linearRampToValueAtTime(peak, start + attack)
  g.gain.setValueAtTime(peak, sustainEnd)
  g.gain.exponentialRampToValueAtTime(0.0001, start + dur)

  // Soft low-pass keeps the buzzy edge off square/sawtooth.
  const filter = c.createBiquadFilter()
  filter.type = 'lowpass'
  filter.frequency.setValueAtTime(Math.max(freq, endFreq ?? freq) * 4, start)
  filter.Q.setValueAtTime(0.7, start)

  osc.connect(filter).connect(g).connect(c.destination)
  osc.start(start)
  osc.stop(start + dur + 0.05)
}

function _chord(notes: VoiceOptions[]) {
  notes.forEach(_voice)
}

// ---------- Public API ----------

function _play(name: string, fallback: () => void) {
  // Sample first; if it isn't there, the procedural fallback runs.
  if (_playSample(name)) return
  fallback()
}

export const audio = {
  /**
   * MUST be called from a user-gesture handler. Browsers refuse to
   * start an AudioContext otherwise. Hooked by AudioPrimer in App.tsx.
   */
  unlock() {
    if (_unlocked) return
    const c = _create()
    void c.resume().then(() => {
      _unlocked = true
      // Near-silent priming tone — some iOS / Safari versions need an
      // actual audio event during the gesture, not just resume().
      _voice({ freq: 1, durationMs: 30, peak: 0.0001 })
    })
  },

  /** Soft countdown tick. */
  tick() {
    _play('sfx_tick', () => {
      _voice({ freq: 880, durationMs: 70, peak: 0.10, type: 'sine' })
    })
  },

  /** Final-second urgent tick — pitch sweeps up. */
  tickFinal() {
    _play('sfx_tick_final', () => {
      _voice({ freq: 900, endFreq: 1500, durationMs: 140, peak: 0.18, type: 'triangle' })
    })
  },

  /** Jackbox-style ding-up sweep on answer lock. */
  lockIn() {
    _play('sfx_lock', () => {
      _chord([
        { freq: 600, endFreq: 1200, durationMs: 220, peak: 0.18, type: 'triangle' },
        { freq: 900, endFreq: 1800, durationMs: 220, peak: 0.10, type: 'sine', detuneCents: 7 },
        { freq: 1200, endFreq: 2400, durationMs: 180, peak: 0.06, type: 'sine', delayMs: 40 },
      ])
    })
  },

  /** Ascending major-third bell on a correct answer. */
  correct() {
    _play('sfx_correct', () => {
      // C5 (523), E5 (659), G5 (784) stacked + a higher accent
      _chord([
        { freq: 523, durationMs: 350, peak: 0.18, type: 'triangle' },
        { freq: 659, durationMs: 350, peak: 0.14, type: 'sine', delayMs: 60 },
        { freq: 784, durationMs: 400, peak: 0.16, type: 'triangle', delayMs: 120 },
        { freq: 1568, durationMs: 200, peak: 0.06, type: 'sine', delayMs: 200 },
      ])
    })
  },

  /** Descending thud on a wrong answer. */
  wrong() {
    _play('sfx_wrong', () => {
      _chord([
        { freq: 240, endFreq: 90, durationMs: 380, peak: 0.22, type: 'sawtooth' },
        { freq: 120, endFreq: 45, durationMs: 380, peak: 0.18, type: 'sine' },
      ])
    })
  },

  /** Short stinger before tier badge reveal. */
  reveal() {
    _play('sfx_reveal', () => {
      _chord([
        { freq: 440, durationMs: 110, peak: 0.16, type: 'square' },
        { freq: 660, durationMs: 110, peak: 0.10, type: 'square', delayMs: 30 },
      ])
    })
  },

  /** Match-end crescendo — Cmaj climb to high C. */
  matchEnd() {
    _play('sfx_match_end', () => {
      const notes = [
        { freq: 261.63, t: 0 },     // C4
        { freq: 329.63, t: 130 },   // E4
        { freq: 392.00, t: 260 },   // G4
        { freq: 523.25, t: 390 },   // C5
        { freq: 659.25, t: 520 },   // E5
        { freq: 1046.5, t: 700 },   // C6 — finale
      ]
      notes.forEach((n, i) =>
        _voice({
          freq: n.freq,
          durationMs: i === notes.length - 1 ? 500 : 250,
          peak: 0.18 + i * 0.01,
          type: 'triangle',
          delayMs: n.t,
        }),
      )
      // Sub-bass undertone
      _voice({
        freq: 65.41,
        durationMs: 1100,
        peak: 0.10,
        type: 'sine',
        delayMs: 0,
      })
    })
  },

  /** Question card reveal sweep. */
  questionShow() {
    _play('sfx_question_show', () => {
      _chord([
        { freq: 440, endFreq: 660, durationMs: 220, peak: 0.14, type: 'sine' },
        { freq: 880, durationMs: 180, peak: 0.06, type: 'sine', delayMs: 100 },
      ])
    })
  },
}
