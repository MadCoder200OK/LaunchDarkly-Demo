// Local development proxy keeps browser API calls same-origin; Python owns server credentials.
import { defineConfig } from 'vite';

export default defineConfig({
  esbuild: { jsx: 'automatic' },
  // The root launcher supplies a matching API port; standalone IDE startup still defaults to 8000.
  server: { port: 5173, strictPort: true, proxy: { '/api': { target: `http://127.0.0.1:${process.env.DEMO_API_PORT || 8000}` } } },
});
