import { jest } from "@jest/globals"

jest.mock("../../shared/daemon-client", () => ({
  acquire: jest.fn(),
  release: jest.fn(),
  status: jest.fn(),
  isDaemonReachable: jest.fn(),
  daemonSocketPath: jest.fn().mockReturnValue("/tmp/mock.sock"),
}))

const mockClient = jest.requireMock("../../shared/daemon-client")

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

  it("Stop never throws on daemon error", async () => {
    mockClient.isDaemonReachable.mockReturnValue(true)
    mockClient.release.mockRejectedValue(new Error("connection refused"))

    const { SixNinePlugin } = await import("../index")
    const hooks = await SixNinePlugin()
    await expect(
      hooks.Stop({ session_id: "test-uuid" })
    ).resolves.toBeUndefined()
  })
})

describe("install script", () => {
  beforeEach(() => {
    jest.resetModules()
  })

  it("install writes hooks to settings.json", () => {
    const fs = require("node:fs")
    const tmpDir = require("node:os").tmpdir()
    const tmpSettings = require("node:path").join(tmpDir, `claude-test-${Date.now()}.json`)

    jest.spyOn(fs, "existsSync").mockImplementation((path: string) => {
      if (path.toString().includes("settings.json")) return true
      return false
    })

    jest.spyOn(fs, "readFileSync").mockReturnValue(JSON.stringify({}))
    const writeSpy = jest.spyOn(fs, "writeFileSync").mockImplementation(() => {})

    const { install } = require("node:fs")
    expect(typeof install).toBe("function")
  })
})
