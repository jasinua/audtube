import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // expose on LAN so you can open it from your phone
    proxy: {
      // Forward API calls to the FastAPI backend during development.
      '/api': 'http://localhost:8000',
    },
  },
})
