import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'url'
import { dirname, resolve } from 'path'

// 获取当前文件的目录路径（在ESM中替代__dirname）
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return

          if (id.includes('echarts')) {
            return 'vendor-echarts'
          }

          if (
            id.includes('naive-ui') ||
            id.includes('@css-render') ||
            id.includes('/vooks/') ||
            id.includes('/evtd/')
          ) {
            return 'vendor-naive-ui'
          }

          if (id.includes('@vicons/')) {
            return 'vendor-icons'
          }

          if (id.includes('html2canvas')) {
            return 'vendor-html2canvas'
          }

          if (id.includes('/axios/')) {
            return 'vendor-axios'
          }

          if (id.includes('@vue') || id.includes('/vue/') || id.includes('vue-router') || id.includes('pinia')) {
            return 'vendor-vue'
          }

          if (id.includes('markdown-it') || id.includes('marked')) {
            return 'vendor-markdown'
          }
        }
      }
    }
  },
  server: {
    cors: true,
    hmr: {
      // 解决WebSocket连接问题
      host: 'localhost',
      port: 5173,
      protocol: 'ws'
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8888',
        changeOrigin: true,
      }
    },
  },
})
