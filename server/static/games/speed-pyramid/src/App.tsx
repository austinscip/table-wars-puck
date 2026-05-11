import { BrowserRouter, Routes, Route } from 'react-router-dom'
import TitleScreen from './screens/TitleScreen'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<TitleScreen />} />
        {/* Routes added in later slices: /pair, /countdown/:code, /question/:code, /scoreboard/:code */}
        <Route path="*" element={<TitleScreen />} />
      </Routes>
    </BrowserRouter>
  )
}
