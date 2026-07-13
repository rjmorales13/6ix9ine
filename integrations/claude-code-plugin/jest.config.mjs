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
  collectCoverageFrom: ["index.ts", "install.ts"],
  coverageThreshold: {
    global: { branches: 70, functions: 80, lines: 80, statements: 80 },
  },
}
