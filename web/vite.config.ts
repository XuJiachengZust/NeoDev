import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    // 局域网访问时放开 Host 校验，避免 IP 访问被拦截导致黑屏
    allowedHosts: true,
    hmr: {
      clientPort: 5173,
    },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // SSE 请求：禁用缓冲
            if (req.headers.accept?.includes('text/event-stream')) {
              proxyReq.setHeader('X-Accel-Buffering', 'no');
            }
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            // SSE 响应：禁用缓冲
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              proxyRes.headers['x-accel-buffering'] = 'no';
            }
          });
        },
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
