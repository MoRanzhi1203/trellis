import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 后端端口。修改 scripts/start.ps1 的 -Port 时请同步这里。
const API_TARGET = 'http://127.0.0.1:8123'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})

