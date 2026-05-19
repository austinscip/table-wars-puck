import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import TitleScreen from './screens/TitleScreen'
import PairScreen from './screens/PairScreen'
import LobbyScreen from './screens/LobbyScreen'
import CountdownScreen from './screens/CountdownScreen'
import QuestionScreen from './screens/QuestionScreen'
import ScoreboardScreen from './screens/ScoreboardScreen'
import { audio } from './lib/audio'

// Sandbox / dev tooling gate (see CONTEXT.md "VITE_DEV_TOOLS" entry +
// docs/adr/0002). When false at build time the Hub module is tree-shaken
// out of the bundle entirely.
const DEV_TOOLS_ENABLED = import.meta.env.VITE_DEV_TOOLS === '1'
const Hub = DEV_TOOLS_ENABLED ? lazy(() => import('./dev/Hub')) : null

/**
 * Hands-free audio-unlock primer. The bar TV is passive — nobody clicks
 * it. Browsers normally block HTMLAudio + Web Audio from playing without
 * a user gesture. Workaround: a 1×1 muted autoplay video grants the page
 * "media engagement," and Chrome (since 66) then lets unmuted audio play
 * without an explicit click. The video's onPlay handler ALSO resumes the
 * Web Audio context so procedural SFX work too. Click/keydown/touchstart
 * remain as a safety-net unlock, but the user should never have to.
 */
function AudioPrimer() {
  useEffect(() => {
    function unlock() { audio.unlock() }
    document.addEventListener('click', unlock, { once: true })
    document.addEventListener('keydown', unlock, { once: true })
    document.addEventListener('touchstart', unlock, { once: true })
    audio.unlock()
    return () => {
      document.removeEventListener('click', unlock)
      document.removeEventListener('keydown', unlock)
      document.removeEventListener('touchstart', unlock)
    }
  }, [])
  return (
    <video
      autoPlay
      muted
      loop
      playsInline
      aria-hidden
      onPlay={() => audio.unlock()}
      onLoadedData={() => audio.unlock()}
      style={{
        position: 'fixed',
        width: 1,
        height: 1,
        opacity: 0,
        pointerEvents: 'none',
        bottom: 0,
        right: 0,
      }}
      src="/static/games/speed-pyramid/audio/silent.mp4"
    />
  )
}

export default function App() {
  return (
    <BrowserRouter basename="/tv/speed-pyramid">
      <AudioPrimer />
      <Routes>
        <Route path="/" element={<TitleScreen />} />
        <Route path="/pair" element={<PairScreen />} />
        <Route path="/lobby/:lobbyCode" element={<LobbyScreen />} />
        <Route path="/countdown/:sessionCode" element={<CountdownScreen />} />
        <Route path="/question/:sessionCode" element={<QuestionScreen />} />
        <Route path="/scoreboard/:sessionCode" element={<ScoreboardScreen />} />
        {Hub && (
          <Route
            path="/dev/hub"
            element={
              <Suspense fallback={<div className="p-8">loading hub…</div>}>
                <Hub />
              </Suspense>
            }
          />
        )}
        <Route path="*" element={<TitleScreen />} />
      </Routes>
    </BrowserRouter>
  )
}
