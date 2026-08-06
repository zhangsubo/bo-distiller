import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'sse-no-request-timeout',
      // Node dev server 默认 requestTimeout=300s，会掐断经代理的 SSE 长连接
      configureServer(server) {
        if (server.httpServer) {
          server.httpServer.requestTimeout = 0;
        }
      },
    },
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
});
