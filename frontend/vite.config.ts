import { defineConfig, type UserConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// Host development uses the project's loopback mapping. Docker supplies an
// explicit VITE_API_PROXY_TARGET=http://backend:8000 in docker-compose.yml.
export function createViteConfig(apiTarget = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:18001'): UserConfig {
  return {
    plugins: [vue()],
    server: { proxy: { '/api': apiTarget }, allowedHosts: true },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            vue: ['vue', 'vue-router'],
            element: ['@element-plus/icons-vue'],
            http: ['axios'],
          },
        },
      },
    },
    test: { environment: 'node', exclude: ['e2e/**', '**/node_modules/**'] },
  }
}
export default defineConfig(createViteConfig())
