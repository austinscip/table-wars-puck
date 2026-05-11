import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Relative base so Flask can serve the built bundle at any subpath
// (e.g. /tv/speed-pyramid/) without rewriting asset URLs.
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
})
