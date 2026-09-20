import { defineConfig } from "vite";

export default defineConfig({
  server: {
    proxy: {
      "/health": "http://localhost:8000",
      "/sources": "http://localhost:8000",
      "/runs": "http://localhost:8000",
      "/products": "http://localhost:8000",
      "/variants": "http://localhost:8000",
      "/discovery": "http://localhost:8000",
    },
  },
});
