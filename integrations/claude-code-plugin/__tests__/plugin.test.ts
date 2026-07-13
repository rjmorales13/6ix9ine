import { jest } from "@jest/globals"
import { mkdtempSync, writeFileSync, readFileSync, existsSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"

jest.mock("../../shared/daemon-client", () => ({
  acquire: jest.fn(),
  release: jest.fn(),
  status: jest.fn(),
  isDaemonReachable: jest.fn(),
  daemonSocketPath: jest.fn().mockReturnValue("/tmp/mock.sock"),
}))

type AnyMock = jest.Mock<(...args: any[]) => any>
const mockClient = jest.requireMock("../../shared/daemon-client") as {
  acquire: AnyMock
  release: AnyMock
  status: AnyMock
  isDaemonReachable: AnyMock
  daemonSocketPath: AnyMock
}

beforeEach(() => {
  jest.clearAllMocks()
})

describe("plugin.json", () => {
  it("has valid manifest schema", () => {
    const manifest = require("../plugin.json")
    expect(manifest.name).toBe("6ix9ine")
    expect(manifest.version).toBe("1.0.0")
    expect(manifest.capabilities.hooks).toContain("UserPromptSubmit")
    expect(manifest.capabilities.hooks).toContain("Stop")
  })
})

describe("SixNinePlugin hooks", () => {
  it("UserPromptSubmit calls acquire when reachable", async () => {
    mockClient.isDaemonReachable.mockReturnValue(true)
    mockClient.acquire.mockResolvedValue({ ok: true })

    const { SixNinePlugin } = await import("../index")
    const hooks = await SixNinePlugin()
    await hooks.UserPromptSubmit({ session_id: "test-uuid", prompt: "hello" })

    expect(mockClient.acquire).toHaveBeenCalledWith("test-uuid", "hello")
  })

  it("UserPromptSubmit is no-op when daemon unreachable", async () => {
    mockClient.isDaemonReachable.mockReturnValue(false)

    const { SixNinePlugin } = await import("../index")
    const hooks = await SixNinePlugin()
    await hooks.UserPromptSubmit({ session_id: "test-uuid", prompt: "hello" })

    expect(mockClient.acquire).not.toHaveBeenCalled()
  })

  it("UserPromptSubmit handles empty session_id gracefully", async () => {
    mockClient.isDaemonReachable.mockReturnValue(true)

    const { SixNinePlugin } = await import("../index")
    const hooks = await SixNinePlugin()
    await hooks.UserPromptSubmit({ session_id: "", prompt: "hello" })

    expect(mockClient.acquire).not.toHaveBeenCalled()
  })

  it("UserPromptSubmit never throws on daemon error", async () => {
    mockClient.isDaemonReachable.mockReturnValue(true)
    mockClient.acquire.mockRejectedValue(new Error("connection refused"))

    const { SixNinePlugin } = await import("../index")
    const hooks = await SixNinePlugin()
    await expect(
      hooks.UserPromptSubmit({ session_id: "test-uuid", prompt: "hello" })
    ).resolves.toBeUndefined()
  })

  it("Stop calls release when reachable", async () => {
    mockClient.isDaemonReachable.mockReturnValue(true)
    mockClient.release.mockResolvedValue({ ok: true })

    const { SixNinePlugin } = await import("../index")
    const hooks = await SixNinePlugin()
    await hooks.Stop({ session_id: "test-uuid" })

    expect(mockClient.release).toHaveBeenCalledWith("test-uuid")
  })

  it("Stop is no-op when daemon unreachable", async () => {
    mockClient.isDaemonReachable.mockReturnValue(false)

    const { SixNinePlugin } = await import("../index")
    const hooks = await SixNinePlugin()
    await hooks.Stop({ session_id: "test-uuid" })

    expect(mockClient.release).not.toHaveBeenCalled()
  })

  it("Stop handles empty session_id gracefully", async () => {
    mockClient.isDaemonReachable.mockReturnValue(true)

    const { SixNinePlugin } = await import("../index")
    const hooks = await SixNinePlugin()
    await hooks.Stop({ session_id: "" })

    expect(mockClient.release).not.toHaveBeenCalled()
  })

  it("Stop never throws on daemon error", async () => {
    mockClient.isDaemonReachable.mockReturnValue(true)
    mockClient.release.mockRejectedValue(new Error("connection refused"))

    const { SixNinePlugin } = await import("../index")
    const hooks = await SixNinePlugin()
    await expect(hooks.Stop({ session_id: "test-uuid" })).resolves.toBeUndefined()
  })

  it("PreToolUse is a no-op when daemon unreachable", async () => {
    mockClient.isDaemonReachable.mockReturnValue(false)

    const { SixNinePlugin } = await import("../index")
    const hooks = await SixNinePlugin()
    await expect(
      hooks.PreToolUse({
        session_id: "test-uuid",
        tool_input: { command: "sleep 1", run_in_background: true },
      })
    ).resolves.toBeUndefined()
  })

  it("PreToolUse returns without error when reachable", async () => {
    mockClient.isDaemonReachable.mockReturnValue(true)

    const { SixNinePlugin } = await import("../index")
    const hooks = await SixNinePlugin()
    await expect(
      hooks.PreToolUse({
        session_id: "test-uuid",
        tool_input: { command: "echo hi" },
      })
    ).resolves.toBeUndefined()
  })
})

describe("install script", () => {
  let dir: string
  let settingsPath: string
  // Prevent auto-run of main() at import; also silence console.error noise.
  let errSpy: jest.SpiedFunction<typeof console.error>

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "6ix9ine-plugin-"))
    settingsPath = join(dir, "settings.json")
    errSpy = jest.spyOn(console, "error").mockImplementation(() => {})
  })

  afterEach(() => {
    errSpy.mockRestore()
    rmSync(dir, { recursive: true, force: true })
  })

  it("resolvePythonPath returns an existing python3 executable, not the Node binary", () => {
    const { resolvePythonPath } = require("../install")
    const python = resolvePythonPath()
    expect(typeof python).toBe("string")
    expect(python.length).toBeGreaterThan(0)
    expect(existsSync(python)).toBe(true)
    expect(python).toContain("python3")
    // Regression guard for BLOCKING-2: must not be the Node.js binary.
    expect(python).not.toBe(process.execPath)
  })

  it("resolvePythonPath honors SIXNINE_PYTHON override", () => {
    const { resolvePythonPath } = require("../install")
    const prev = process.env.SIXNINE_PYTHON
    try {
      process.env.SIXNINE_PYTHON = process.execPath // any existing file
      expect(resolvePythonPath()).toBe(process.execPath)
    } finally {
      if (prev === undefined) delete process.env.SIXNINE_PYTHON
      else process.env.SIXNINE_PYTHON = prev
    }
  })

  it("resolvePythonPath throws when SIXNINE_PYTHON points at a missing file", () => {
    const { resolvePythonPath } = require("../install")
    const prev = process.env.SIXNINE_PYTHON
    try {
      process.env.SIXNINE_PYTHON = join(dir, "nope-python3")
      expect(() => resolvePythonPath()).toThrow(/SIXNINE_PYTHON/)
    } finally {
      if (prev === undefined) delete process.env.SIXNINE_PYTHON
      else process.env.SIXNINE_PYTHON = prev
    }
  })

  it("install writes UserPromptSubmit and Stop hooks with a python3 command", () => {
    const { install, ACQUIRE_CODE, RELEASE_CODE } = require("../install")
    writeFileSync(settingsPath, JSON.stringify({}))

    expect(install(settingsPath)).toBe(true)

    const settings = JSON.parse(readFileSync(settingsPath, "utf-8"))
    const acquireEntry = settings.hooks.UserPromptSubmit[0].hooks[0]
    const releaseEntry = settings.hooks.Stop[0].hooks[0]

    expect(acquireEntry.type).toBe("command")
    expect(acquireEntry.command).toContain("python3")
    expect(acquireEntry.command).not.toBe(process.execPath)
    // No shell interpolation: python code is passed via an argv array, not a
    // single interpolated command string.
    expect(acquireEntry.args).toEqual(["-c", ACQUIRE_CODE])
    expect(releaseEntry.args).toEqual(["-c", RELEASE_CODE])
  })

  it("install is idempotent — running twice does not duplicate hooks", () => {
    const { install } = require("../install")
    writeFileSync(settingsPath, JSON.stringify({}))

    install(settingsPath)
    install(settingsPath)

    const settings = JSON.parse(readFileSync(settingsPath, "utf-8"))
    expect(settings.hooks.UserPromptSubmit).toHaveLength(1)
    expect(settings.hooks.Stop).toHaveLength(1)
  })

  it("install returns false when settings.json is missing", () => {
    const { install } = require("../install")
    expect(install(join(dir, "does-not-exist.json"))).toBe(false)
  })

  it("uninstall removes the hooks it installed", () => {
    const { install, uninstall } = require("../install")
    writeFileSync(settingsPath, JSON.stringify({}))

    install(settingsPath)
    expect(uninstall(settingsPath)).toBe(true)

    const settings = JSON.parse(readFileSync(settingsPath, "utf-8"))
    expect(settings.hooks.UserPromptSubmit).toBeUndefined()
    expect(settings.hooks.Stop).toBeUndefined()
  })

  it("main() installs hooks into the given settings path", () => {
    const { main } = require("../install")
    mockClient.isDaemonReachable.mockReturnValue(false)
    writeFileSync(settingsPath, JSON.stringify({}))

    main(settingsPath)

    const settings = JSON.parse(readFileSync(settingsPath, "utf-8"))
    expect(settings.hooks.UserPromptSubmit).toHaveLength(1)
  })

  it("main() with --uninstall removes hooks", () => {
    const { install, main } = require("../install")
    writeFileSync(settingsPath, JSON.stringify({}))
    install(settingsPath)

    const prevArgv = process.argv
    try {
      process.argv = [...prevArgv, "--uninstall"]
      main(settingsPath)
    } finally {
      process.argv = prevArgv
    }

    const settings = JSON.parse(readFileSync(settingsPath, "utf-8"))
    expect(settings.hooks.UserPromptSubmit).toBeUndefined()
  })
})
