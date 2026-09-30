import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  appType: 'spa',
  build: {
    target: 'es2022',
    cssCodeSplit: true,
    sourcemap: false,
    reportCompressedSize: false,
    assetsInlineLimit: 2048,
    modulePreload: { polyfill: true },
    rollupOptions: {
      output: {
        // Keep the marketing shell light; pull Three/R3F only on /world/*.
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('three') || id.includes('@react-three') || id.includes('maath')) {
            return 'world-3d'
          }
          if (id.includes('react-router')) return 'router'
          if (id.includes('lenis')) return 'motion'
          if (id.includes('react-dom') || id.includes('/react/')) return 'react-vendor'
        },
      },
    },
    chunkSizeWarningLimit: 1100,
  },
  server: {
    headers: {
      'Cache-Control': 'no-store',
    },
  },
  preview: {
    headers: {
      'Cache-Control': 'public, max-age=600',
    },
  },
})
