import { BrowserRouter, Routes, Route } from 'react-router-dom'
import TitleScreen from './screens/TitleScreen'
import PairScreen from './screens/PairScreen'
import CountdownScreen from './screens/CountdownScreen'
import QuestionScreen from './screens/QuestionScreen'
import ScoreboardScreen from './screens/ScoreboardScreen'

export default function App() {
  return (
    <BrowserRouter basename="/tv/speed-pyramid">
      <Routes>
        <Route path="/" element={<TitleScreen />} />
        <Route path="/pair" element={<PairScreen />} />
        <Route path="/countdown/:sessionCode" element={<CountdownScreen />} />
        <Route path="/question/:sessionCode" element={<QuestionScreen />} />
        <Route path="/scoreboard/:sessionCode" element={<ScoreboardScreen />} />
        <Route path="*" element={<TitleScreen />} />
      </Routes>
    </BrowserRouter>
  )
}
