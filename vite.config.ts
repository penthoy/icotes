import path from "path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const env = loadEnv(mode, process.cwd(), '');
  
  // Auto-substitute {PROJECT_ROOT} with actual project path
  const projectRoot = process.cwd();
  const processedEnv: Record<string, string> = {};
  
  // Process all VITE_ prefixed environment variables
  Object.keys(env).forEach(key => {
    if (key.startsWith('VITE_')) {
      let value = env[key];
      // Replace {PROJECT_ROOT} with actual project root path
      if (value && value.includes('{PROJECT_ROOT}')) {
        value = value.replace(/{PROJECT_ROOT}/g, projectRoot);
        console.log(`🔧 Vite Config: Substituted ${key}: ${env[key]} → ${value}`);
      }
      processedEnv[key] = value;
    }
  });

  return {
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
    define: {
      // Make processed env vars available to the app
      ...Object.keys(processedEnv).reduce((acc, key) => {
        acc[`import.meta.env.${key}`] = JSON.stringify(processedEnv[key]);
        return acc;
      }, {} as Record<string, string>),
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
  };
});
