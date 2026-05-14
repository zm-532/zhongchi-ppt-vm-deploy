import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: "e2e.spec.ts",
  timeout: 120_000,
  use: {
    baseURL: "http://127.0.0.1:3101",
  },
  webServer: [
    {
      command: "uv run uvicorn app.main:app --host 127.0.0.1 --port 8100",
      cwd: "../backend",
      url: "http://127.0.0.1:8100/api/projects",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3101",
      cwd: ".",
      env: {
        NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8100",
      },
      url: "http://127.0.0.1:3101",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
