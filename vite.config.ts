import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_TARGET || 'http://114.55.111.100:8002'
  const wsTarget = env.VITE_WS_TARGET || apiTarget.replace(/^http/, 'ws')

  return {
    plugins: [vue()],
    server: {
      port: 8021,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true
        },
        '/webSocket': {
          target: wsTarget,
          changeOrigin: true,
          ws: true
        }
      }
    }
  }
})
