import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

// https://vitejs.dev/config/
export default defineConfig({
  base: process.env.NODE_ENV === "development" ? "/" : process.env.VITE_BASE_PATH || "/",
  optimizeDeps: {
    entries: ["src/main.tsx"],
  },
  plugins: [
    react(),
  ],
  resolve: {
    preserveSymlinks: true,
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: process.env.FRONTEND_HOST || process.env.SITE_URL || '0.0.0.0',
    port: parseInt(process.env.FRONTEND_PORT || '5173'),
    // @ts-ignore
    allowedHosts: true,
    proxy: {
      '/ws': {
        target: process.env.VITE_WS_URL || `ws://${process.env.SITE_URL || '0.0.0.0'}:${process.env.PORT || '8000'}`,
        ws: true,
        changeOrigin: true,
        secure: false,
      },
      '/api': {
        target: process.env.VITE_API_URL || `http://${process.env.SITE_URL || '0.0.0.0'}:${process.env.PORT || '8000'}`,
        changeOrigin: true,
      },
      '/execute': {
        target: process.env.VITE_API_URL || `http://${process.env.SITE_URL || '0.0.0.0'}:${process.env.PORT || '8000'}`,
        changeOrigin: true,
      },
      '/health': {
        target: process.env.VITE_API_URL || `http://${process.env.SITE_URL || '0.0.0.0'}:${process.env.PORT || '8000'}`,
        changeOrigin: true,
      },
    },
  }
});
