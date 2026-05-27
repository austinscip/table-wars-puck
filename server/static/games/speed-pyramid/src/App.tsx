import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom'
import TitleScreen from './screens/TitleScreen'
import PairScreen from './screens/PairScreen'
import LobbyScreen from './screens/LobbyScreen'
import CountdownScreen from './screens/CountdownScreen'
import QuestionScreen from './screens/QuestionScreen'
import ScoreboardScreen from './screens/ScoreboardScreen'
import CategoryPickScreen from './screens/CategoryPickScreen'
import MinigameScreen from './screens/MinigameScreen'
import { audio } from './lib/audio'
import { getSocket } from './lib/socket'

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

/**
 * One-shot subscription to the `lobby_cancelled` server broadcast that
 * fires whenever /api/pair/clear runs (Hub "Reset all" or a per-puck
 * "Back to start"). Lives at the App level instead of inlined into every
 * screen so a single listener wins regardless of which route the TV is
 * parked on. `replace: true` prevents the back button from sending the
 * TV back to a stale scoreboard / countdown.
 */
function GlobalLobbyResetListener() {
  const navigate = useNavigate()
  useEffect(() => {
    const socket = getSocket()
    function onLobbyCancelled() {
      // The Hub IS the thing that triggered the reset; it shouldn't
      // bounce itself away from /dev/hub. Skip the navigation for any
      // tab currently on a dev route.
      if (window.location.pathname.startsWith('/tv/speed-pyramid/dev/')) {
        return
      }
      navigate('/', { replace: true })
    }
    socket.on('lobby_cancelled', onLobbyCancelled)
    return () => {
      socket.off('lobby_cancelled', onLobbyCancelled)
    }
  }, [navigate])
  return null
}

// Tiny build marker so we can tell from across the room whether a tab
// has the latest bundle loaded. Skipped on /dev/hub (the Hub has its
// own chip in the header).
function BuildChip() {
  if (window.location.pathname.startsWith('/tv/speed-pyramid/dev/')) {
    return null
  }
  return (
    <div
      style={{
        position: 'fixed',
        top: 8,
        right: 8,
        zIndex: 1000,
        background: '#fbbf24',
        color: '#000',
        padding: '2px 6px',
        borderRadius: 4,
        fontFamily: 'monospace',
        fontSize: 10,
        fontWeight: 600,
        textTransform: 'uppercase',
        pointerEvents: 'none',
      }}
    >
      build May-26 b866c2d-tv
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter basename="/tv/speed-pyramid">
      <AudioPrimer />
      <GlobalLobbyResetListener />
      <BuildChip />
      <Routes>
        <Route path="/" element={<TitleScreen />} />
        <Route path="/pair" element={<PairScreen />} />
        <Route path="/lobby/:lobbyCode" element={<LobbyScreen />} />
        <Route path="/countdown/:sessionCode" element={<CountdownScreen />} />
        <Route path="/category-pick/:sessionCode" element={<CategoryPickScreen />} />
        <Route path="/minigame/:sessionCode" element={<MinigameScreen />} />
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
