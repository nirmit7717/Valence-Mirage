import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const isDev = process.env.NODE_ENV === 'development'
export default defineConfig({
  plugins: [react()],
  base: isDev ? '/' : '/static/',
  server: {
    host: true,
    proxy: {
      '/session': 'http://localhost:8000',
      '/sessions': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
      '/user': 'http://localhost:8000',
    }
  },
  build: {
    outDir: '../backend/static',
    emptyOutDir: false,
  }
})
