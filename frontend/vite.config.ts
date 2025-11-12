import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // Allow external access
    allowedHosts: [
      'localhost',
      'khanhan-lytutrong.site',
      '.khanhan-lytutrong.site', // Wildcard subdomain
    ],
  },
});
