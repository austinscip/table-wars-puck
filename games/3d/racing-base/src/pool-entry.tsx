import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { PoolGame } from './PoolGame'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PoolGame />
  </StrictMode>,
)
