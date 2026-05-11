import { BrowserRouter, Routes, Route } from 'react-router-dom'
import TitleScreen from './screens/TitleScreen'
import PairScreen from './screens/PairScreen'
import CountdownScreen from './screens/CountdownScreen'

export default function App() {
  return (
    <BrowserRouter basename="/tv/speed-pyramid">
      <Routes>
        <Route path="/" element={<TitleScreen />} />
        <Route path="/pair" element={<PairScreen />} />
        <Route path="/countdown/:sessionCode" element={<CountdownScreen />} />
        {/* /question/:code (1C), /scoreboard/:code (1D) land later */}
        <Route path="*" element={<TitleScreen />} />
      </Routes>
    </BrowserRouter>
  )
}
