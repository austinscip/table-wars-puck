import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import TitleScreen from './screens/TitleScreen'
import PairScreen from './screens/PairScreen'
import LobbyScreen from './screens/LobbyScreen'
import CountdownScreen from './screens/CountdownScreen'
import QuestionScreen from './screens/QuestionScreen'
import ScoreboardScreen from './screens/ScoreboardScreen'
import { audio } from './lib/audio'

/**
 * Silent audio-unlock primer. Browser autoplay policies require a user
 * gesture before an AudioContext can produce sound. We attach a one-shot
 * listener for any click / keydown / touchstart on the document — the
 * first interaction unlocks audio, no UI banner required.
 */
function AudioPrimer() {
  useEffect(() => {
    function unlock() { audio.unlock() }
    document.addEventListener('click', unlock, { once: true })
    document.addEventListener('keydown', unlock, { once: true })
    document.addEventListener('touchstart', unlock, { once: true })
    return () => {
      document.removeEventListener('click', unlock)
      document.removeEventListener('keydown', unlock)
      document.removeEventListener('touchstart', unlock)
    }
  }, [])
  return null
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
        <Route path="*" element={<TitleScreen />} />
      </Routes>
    </BrowserRouter>
  )
}
