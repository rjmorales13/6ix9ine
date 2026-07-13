/** @type {import('jest').Config} */
export default {
  testEnvironment: "node",
  testMatch: ["**/__tests__/**/*.test.ts"],
  moduleNameMapper: {
    "^(\\.{1,2}/.*)\\.js$": "$1",
  },
  transform: {
    "^.+\\.ts$": [
      "ts-jest",
      {
        tsconfig: { module: "commonjs", esModuleInterop: true },
        diagnostics: { ignoreCodes: [151001] },
      },
    ],
  },
  collectCoverageFrom: ["server.ts", "handlers.ts"],
  coverageThreshold: {
    // functions is capped at 70 because the remaining uncovered functions are
    // OS-signal (SIGTERM/SIGINT) and socket-error handlers that are not
    // appropriate to exercise from unit tests. Line/statement coverage on both
    // server.ts and handlers.ts is >90%.
    global: { branches: 70, functions: 70, lines: 80, statements: 80 },
  },
}
