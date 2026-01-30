import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [vue()],
    base: env.VITE_BASE_PATH || '/', // Support subpath deployment
    server: {
      port: parseInt(env.VITE_PORT) || 3000,
      host: '0.0.0.0'
    }
  }
})
