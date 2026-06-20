import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// 前端单元/组件测试配置（与 vite 构建配置分离，避免污染生产构建）。
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    setupFiles: ['./src/test/setup.ts'],
  },
})
