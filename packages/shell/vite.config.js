import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@frontend": path.resolve(__dirname, "../../frontend"),
    },
  },
  server: {
    port: Number(process.env.APP_PORT || 4000),
    host: "0.0.0.0",
  },
  preview: {
    port: Number(process.env.APP_PORT || 4000),
    host: "0.0.0.0",
  },
});
