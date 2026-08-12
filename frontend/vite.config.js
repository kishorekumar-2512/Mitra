import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// OneDrive-mounted WSL folders often reject native file watches. Polling keeps
// Vite HMR reliable while the project is developed from /mnt/c.
export default defineConfig({
    plugins: [react()],
    server: {
        host: "0.0.0.0",
        watch: { usePolling: true, interval: 500 },
        proxy: { "/api": "http://localhost:8000" },
    },
});
