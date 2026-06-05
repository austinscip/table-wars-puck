// Transposed from server/static/games/speed-pyramid/tokens.json — the
// authoritative brand palette. Keep in sync.

export const colors = {
  bg: '#0A0E1A',
  primary: '#3B82F6',
  accent: '#EC4899',
  correct: '#FBBF24',
  wrong: '#EF4444',
  text: '#F8FAFC',
  textDim: 'rgba(248, 250, 252, 0.6)',
  textFaint: 'rgba(248, 250, 252, 0.4)',
} as const;

export const fonts = {
  // Bundled fonts come later. System fallbacks are picked for closest
  // match: System (UI default) maps reasonably to Inter; monospace is
  // platform default.
  display: 'System',
  body: 'System',
  mono: 'monospace',
} as const;

export const motion = {
  easeOvershoot: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  revealMs: 400,
  snapMs: 150,
  countUpMs: 800,
} as const;
