import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import TitleScreen from './screens/TitleScreen'
import PairScreen from './screens/PairScreen'
import LobbyScreen from './screens/LobbyScreen'
import CountdownScreen from './screens/CountdownScreen'
import QuestionScreen from './screens/QuestionScreen'
import ScoreboardScreen from './screens/ScoreboardScreen'
import { audio } from './lib/audio'

/**
 * Global audio-unlock primer. Browser autoplay policies require a user
 * gesture before any AudioContext can produce sound. The puck flow never
 * forces a click (you go straight to /pair and the puck drives the rest),
 * so we listen for any click / keydown on the document and unlock once.
 * Shows a tiny hint banner until it fires.
 */
function AudioPrimer() {
  const [unlocked, setUnlocked] = useState(false)

  useEffect(() => {
    function unlock() {
      audio.unlock()
      setUnlocked(true)
    }
    document.addEventListener('click', unlock, { once: true })
    document.addEventListener('keydown', unlock, { once: true })
    document.addEventListener('touchstart', unlock, { once: true })
    return () => {
      document.removeEventListener('click', unlock)
      document.removeEventListener('keydown', unlock)
      document.removeEventListener('touchstart', unlock)
    }
  }, [])

  return (
    <AnimatePresence>
      {!unlocked ? (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-full border-2 border-accent/60 bg-bg/90 px-6 py-3 font-body text-sm font-medium text-accent backdrop-blur-sm"
        >
          Click anywhere to enable sound
        </motion.div>
      ) : null}
    </AnimatePresence>
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
        <Route path="*" element={<TitleScreen />} />
      </Routes>
    </BrowserRouter>
  )
}
