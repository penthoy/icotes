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
    build: {
      chunkSizeWarningLimit: 600,
      rollupOptions: {
        output: {
          manualChunks: {
            // React core
            "vendor-react": ["react", "react-dom", "react-router", "react-router-dom"],
            // CodeMirror editor (many packages, all heavy)
            "vendor-codemirror": [
              "@codemirror/autocomplete",
              "@codemirror/commands",
              "@codemirror/language",
              "@codemirror/search",
              "@codemirror/state",
              "@codemirror/view",
              "@codemirror/theme-one-dark",
              "@codemirror/lang-javascript",
              "@codemirror/lang-python",
              "@codemirror/lang-html",
              "@codemirror/lang-css",
              "@codemirror/lang-json",
              "@codemirror/lang-markdown",
              "@codemirror/lang-cpp",
              "@codemirror/lang-go",
              "@codemirror/lang-rust",
              "@codemirror/lang-yaml",
            ],
            // Terminal emulator
            "vendor-xterm": ["@xterm/xterm", "@xterm/addon-fit"],
            // Audio / waveform
            "vendor-audio": ["wavesurfer.js"],
            // Markdown rendering
            "vendor-markdown": [
              "react-markdown",
              "react-syntax-highlighter",
              "rehype-highlight",
              "remark-gfm",
            ],
            // Radix UI components
            "vendor-radix": [
              "@radix-ui/react-accordion",
              "@radix-ui/react-alert-dialog",
              "@radix-ui/react-avatar",
              "@radix-ui/react-checkbox",
              "@radix-ui/react-collapsible",
              "@radix-ui/react-context-menu",
              "@radix-ui/react-dialog",
              "@radix-ui/react-dropdown-menu",
              "@radix-ui/react-hover-card",
              "@radix-ui/react-icons",
              "@radix-ui/react-label",
              "@radix-ui/react-menubar",
              "@radix-ui/react-navigation-menu",
              "@radix-ui/react-popover",
              "@radix-ui/react-progress",
              "@radix-ui/react-radio-group",
              "@radix-ui/react-scroll-area",
              "@radix-ui/react-select",
              "@radix-ui/react-separator",
              "@radix-ui/react-slider",
              "@radix-ui/react-slot",
              "@radix-ui/react-switch",
              "@radix-ui/react-tabs",
              "@radix-ui/react-toast",
              "@radix-ui/react-toggle",
              "@radix-ui/react-tooltip",
            ],
            // Animation
            "vendor-motion": ["framer-motion"],
            // AI SDK
            "vendor-ai": ["ai", "@ai-sdk/react"],
          },
        },
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
        // Clipboard endpoints for terminal copy/paste
        '/clipboard': {
          target: process.env.VITE_API_URL || `http://${process.env.SITE_URL || '0.0.0.0'}:${process.env.PORT || '8000'}`,
          changeOrigin: true,
        },
      },
    }
  };
});
