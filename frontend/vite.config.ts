import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The bundle ships inside the Home Assistant integration, which serves it
// together with the JSON API on its own port.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../custom_components/unifi_people_pointer/webui',
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    proxy: {
      // Dev only: point at a running integration (UPP_API, default localhost:8765).
      '/api': {
        target: process.env.UPP_API || 'http://localhost:8765',
        changeOrigin: true,
      },
    },
  },
});
