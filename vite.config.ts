/**
 * Vite 构建配置文件
 * 
 * @description 配置开发服务器、构建输出、API 代理等
 * @author zhangzhen
 * @version 0.1.0
 */
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), '')
  // API 代理目标地址，默认本地 8002 端口
  const apiTarget = env.VITE_API_TARGET || 'http://127.0.0.1:8002/'
  // WebSocket 代理目标地址，默认与 API 目标一致
  const wsTarget = env.VITE_WS_TARGET || apiTarget.replace(/^http/, 'ws')

  return {
    plugins: [
      // Vue 单文件组件支持
      vue()
    ],
    // 配置入口文件为 index.html
    build: {
      rollupOptions: {
        input: resolve(__dirname, 'index.html')
      }
    },
    // 开发服务器配置
    server: {
      port: 8021,
      host: '0.0.0.0',
      // 配置开发服务器的默认入口文件为 newindex.html
      fs: {
        allow: ['..']
      },
      // API 代理配置
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
