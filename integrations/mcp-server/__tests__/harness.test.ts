import { TOOLS, RESOURCES, handleAcquire, handleRelease, handleStatus, handleHold, getCapabilities } from "../handlers"

jest.mock("../../shared/daemon-client", () => ({
  acquire: jest.fn(),
  release: jest.fn(),
  status: jest.fn(),
  hold: jest.fn(),
  isDaemonReachable: jest.fn().mockReturnValue(true),
  daemonSocketPath: jest.fn().mockReturnValue("/tmp/mock.sock"),
}))

const mockClient = jest.requireMock("../../shared/daemon-client")

beforeEach(() => {
  jest.clearAllMocks()
})

describe("getCapabilities", () => {
  it("returns correct protocol version and server info", () => {
    const caps = getCapabilities()
    expect(caps.protocolVersion).toBe("2025-03-26")
    expect(caps.serverInfo.name).toBe("6ix9ine-mcp-server")
    expect(caps.serverInfo.version).toBe("1.0.0")
    expect(caps.capabilities.tools).toEqual({})
    expect(caps.capabilities.resources.subscribe).toBe(true)
  })
})

describe("TOOLS", () => {
  it("exposes all 4 required tools", () => {
    const names = TOOLS.map((t) => t.name)
    expect(names).toContain("6ix9ine_acquire")
    expect(names).toContain("6ix9ine_release")
    expect(names).toContain("6ix9ine_status")
    expect(names).toContain("6ix9ine_hold")
  })

  it("acquire requires session_id", () => {
    const tool = TOOLS.find((t) => t.name === "6ix9ine_acquire")
    expect(tool?.inputSchema?.required).toContain("session_id")
  })

  it("release requires session_id", () => {
    const tool = TOOLS.find((t) => t.name === "6ix9ine_release")
    expect(tool?.inputSchema?.required).toContain("session_id")
  })

  it("hold requires reason and duration", () => {
    const tool = TOOLS.find((t) => t.name === "6ix9ine_hold")
    expect(tool?.inputSchema?.required).toContain("reason")
    expect(tool?.inputSchema?.required).toContain("duration")
  })
})

describe("RESOURCES", () => {
  it("exposes status resource", () => {
    expect(RESOURCES.some((r) => r.uri === "6ix9ine://status")).toBe(true)
  })
})

describe("handleAcquire", () => {
  it("returns error for empty session_id", async () => {
    const result = await handleAcquire("", "")
    expect(result.isError).toBe(true)
    expect(result.content[0].text).toMatch(/required/)
  })

  it("calls daemon acquire and returns success", async () => {
    mockClient.acquire.mockResolvedValue({ ok: true, status: "ACTIVE", count: 1 })
    const result = await handleAcquire("test-uuid", "test work")
    expect(mockClient.acquire).toHaveBeenCalledWith("test-uuid", "test work")
    expect(result.isError).toBeFalsy()
    expect(result.content[0].text).toMatch(/acquired/)
  })

  it("propagates daemon error", async () => {
    mockClient.acquire.mockResolvedValue({ ok: false, error: "unknown agent" })
    const result = await handleAcquire("test-uuid", "")
    expect(result.isError).toBe(true)
    expect(result.content[0].text).toMatch(/unknown agent/)
  })
})

describe("handleRelease", () => {
  it("returns error for empty session_id", async () => {
    const result = await handleRelease("")
    expect(result.isError).toBe(true)
    expect(result.content[0].text).toMatch(/required/)
  })

  it("calls daemon release and returns success", async () => {
    mockClient.release.mockResolvedValue({ ok: true, status: "IDLE", count: 0 })
    const result = await handleRelease("test-uuid")
    expect(mockClient.release).toHaveBeenCalledWith("test-uuid")
    expect(result.isError).toBeFalsy()
    expect(result.content[0].text).toMatch(/released/)
  })

  it("handles session not found gracefully", async () => {
    mockClient.release.mockResolvedValue({ ok: false, error: "session not found" })
    const result = await handleRelease("gone-uuid")
    expect(result.isError).toBeFalsy()
    expect(result.content[0].text).toMatch(/released/)
  })
})

describe("handleStatus", () => {
  it("returns status from daemon", async () => {
    mockClient.status.mockResolvedValue({ ok: true, status: "ACTIVE", count: 1 })
    const result = await handleStatus()
    expect(result.content[0].text).toContain("ACTIVE")
  })
})

describe("handleHold", () => {
  it("returns error for missing args", async () => {
    const result = await handleHold("", "")
    expect(result.isError).toBe(true)
  })

  it("calls daemon hold", async () => {
    mockClient.hold.mockResolvedValue({ ok: true, hold_id: "hold-abc" })
    const result = await handleHold("30m", "build")
    expect(mockClient.hold).toHaveBeenCalledWith("30m", "build")
    expect(result.isError).toBeFalsy()
    expect(result.content[0].text).toMatch(/hold acquired/)
  })
})
