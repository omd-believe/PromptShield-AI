import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Use '0.0.0.0' so the dev server is reachable inside Docker containers.
    // 'localhost' only binds the loopback interface.
    host: '0.0.0.0',
    port: 5173,
    strictPort: false,
  },
  // Explicitly declare the env variable used by api.js so Vite validates it at build time.
  // Set VITE_API_BASE_URL in your .env or deployment environment.
  // Example: VITE_API_BASE_URL=https://promptshield-backend.onrender.com/api/v1
})
