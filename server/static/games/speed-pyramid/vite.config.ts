import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Absolute base matches the Flask route prefix. Without this, relative
// `./assets/...` URLs break for any deep route (e.g. /tv/speed-pyramid/pair)
// because the browser resolves them off the current path, not off
// index.html. Result was a blank white page on first load.
//
// If the Flask mount point changes, update this string and rebuild.
export default defineConfig({
  base: '/tv/speed-pyramid/',
  plugins: [react(), tailwindcss()],
})
