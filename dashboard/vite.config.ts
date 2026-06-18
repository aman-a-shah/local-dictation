import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: "./" makes all asset URLs relative, so pywebview can load index.html
// straight off the filesystem inside the packaged app.
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
