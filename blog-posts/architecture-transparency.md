# How 6ix9ine Manages System Sleep Without Unnecessary Privilege Escalation

Every keep-awake tool for macOS eventually hits the same wall: truly blocking system sleep — the kind that survives a closed lid on a docked Mac — requires `pmset disablesleep`, and `pmset disablesleep` requires root.

That's an uncomfortable requirement for a convenience utility. It means users are being asked to hand privileged control of their machine's power management to a background process, usually one they can't read. This post walks through how [6ix9ine](https://github.com/rjmorales13/6ix9ine) — a free, MIT-licensed daemon that keeps your Mac awake only while AI agent sessions are running — is architected so that the privileged surface is as small as it can possibly be, and why the whole thing is open source on purpose.

## Why Privilege Escalation Is Risky Here

A keep-awake daemon has three properties that should make you cautious:

1. **It runs forever.** It's a LaunchDaemon or LaunchAgent, alive from boot, not a process you start and audit in the moment.
2. **It wants root.** Not for most of what it does — but the one syscall-adjacent thing it exists to do (`pmset disablesleep`) demands it.
3. **It listens to other processes.** Something has to tell it when to block sleep, which means an IPC surface that arbitrary local code might try to talk to.

The naive design puts all of that in one process: a root daemon that parses config, watches agent processes, runs policy logic, renders status, and calls the power APIs. Now your entire feature set — every JSON parser, every string formatter, every "just one more integration" — runs as root. A bug anywhere is a bug in a root process, and any local attacker who finds the IPC socket gets to negotiate with root directly.

The fix isn't cleverness. It's an old idea: **privilege separation**. Put everything you possibly can in user space, and make the root component so small that reading it takes less time than deciding whether to trust it.

## The Three-Tier Design

6ix9ine splits into three layers with strictly one job each:

```text
┌────────────────────────────────────────────────────┐
│  Layer 1 · Hooks (user space, ephemeral)           │
│  Claude Code / OpenCode lifecycle hooks fire        │
│  "acquire" on session start, "release" on end.     │
└──────────────────────┬─────────────────────────────┘
                       │ Unix socket
┌──────────────────────▼─────────────────────────────┐
│  Layer 2 · Daemon (user space, LaunchAgent)        │
│  Reference-counted session registry. All policy.   │
│  Watches PIDs, expires holds, feeds the dashboard. │
└──────────────────────┬─────────────────────────────┘
                       │ Unix socket, peer-UID checked
┌──────────────────────▼─────────────────────────────┐
│  Layer 3 · Helper (root, LaunchDaemon)             │
│  One mutating endpoint: set_sleep_blocked(bool).   │
│  Calls `pmset disablesleep`. Nothing else.         │
└────────────────────────────────────────────────────┘
```

The hooks know nothing about sleep. The daemon knows nothing about IOKit or `pmset`. The helper knows nothing about agents, sessions, or policy. Root privilege exists in exactly one place, and that place has no configuration surface at all.

## Layer 2: Reference Counting Instead of Toggles

Most keep-awake tools are switches. 6ix9ine is a counter, because the actual question — "is work happening right now?" — is a set-membership question, not a boolean preference.

The registry is a plain in-memory class, deliberately free of sockets, subprocesses, and asyncio so it can be unit tested directly:

```python
@dataclass(frozen=True)
class Session:
    key: str
    agent: str
    reason: str
    timestamp: float
    pid: Optional[int] = None
    turn_open: bool = True
    command_pids: frozenset[CommandPid] = frozenset()


class SessionRegistry:
    """Reference-counted registry of sleep-blocking sessions and timed holds."""

    def count(self) -> int:
        return len(self._sessions) + len(self._holds)

    def is_active(self) -> bool:
        return self.count() > 0
```

Every `acquire` adds a session; every `release` removes one. When `count()` drops to zero, the daemon tells the helper to unblock sleep. Multiple concurrent agents just work — sleep stays blocked until the *last* session ends.

The interesting engineering is in the failure paths. What if an agent crashes without calling release? The daemon records the caller's PID at acquire time and prunes sessions whose process has died:

```python
def prune_dead(self, is_alive: Callable[[int], bool]) -> list[str]:
    return self._prune(lambda s: s.pid is not None and not is_alive(s.pid))
```

Tracked background-command PIDs are additionally anchored by process **creation time**, so PID reuse — the OS handing a dead process's number to a new process — can't fool the pruner into keeping a stale session alive. A leaked sleep block is the failure mode of every toggle-based tool; here it's structurally prevented.

## Layer 3: The Entire Privileged Surface, Annotated

`bin/helper.py` is about 140 lines. This is the complete decision logic for who may talk to it:

```python
def authorize(peer_pid, owner_uid, process_lookup=psutil.Process):
    """Gate mutating helper calls to the single registered owner UID."""
    if peer_pid is None:
        return False, "could not determine caller pid"
    if owner_uid is None:
        return False, "helper has no registered owner; run setup-privileged-helper"
    try:
        caller_uid = process_lookup(peer_pid).uids().real
    except psutil.NoSuchProcess:
        return False, "caller process no longer exists"
    if caller_uid != owner_uid:
        return False, f"caller uid {caller_uid} does not match registered owner {owner_uid}"
    return True, "ok"
```

At install time, the (non-root) installing user's UID is written to an owner file that only root can modify. At request time, the helper resolves the connecting process via the `LOCAL_PEERPID` socket option and rejects any caller whose real UID doesn't match the registered owner. The code comments are honest about the boundary: this is peer-credential checking, not code-signature verification — stated plainly in the source rather than implied by marketing.

And here is everything root actually *does*:

```python
def run_pmset_disablesleep(blocked: bool, run=subprocess.run) -> bool:
    value = "1" if blocked else "0"
    result = run(["pmset", "disablesleep", value],
                 capture_output=True, text=True, timeout=10, check=False)
    return result.returncode == 0
```

A fixed argv list — no shell, no string interpolation, no caller-supplied arguments. The request can influence exactly one bit: blocked or not.

The last piece is the fail-safe. The scariest bug a tool like this could ship is leaving `disablesleep` stuck on after a crash, silently cooking a MacBook in a bag. The helper resets to a known state on both startup and shutdown:

```python
# Safety net: always start from a known-unblocked state, so a crash
# loop or an unclean shutdown can never leave disablesleep stuck at 1.
run_pmset_disablesleep(False)
...
try:
    await server.serve_forever()
finally:
    run_pmset_disablesleep(False)
```

No configuration files. No policy logic. No agent awareness. If you can read Python, you can verify every claim in this section against the source in a few minutes.

## Why Open Source Is the Point, Not a Perk

For most software, open source is a distribution choice. For privilege-escalation software, it's the trust model.

A closed-source keep-awake app asks you to believe three things: that its privileged component does only what the marketing says, that its IPC can't be abused by other local software, and that its failure modes were considered. You can't check any of them. With 6ix9ine, all three are checkable claims — the helper's single endpoint, the `authorize()` gate, and the reset-on-start fail-safe are right there in `bin/helper.py`.

The rest of the system is held to the same standard: 223+ unit and integration tests across the registry, IPC, daemon, helper, and TUI; the privileged path verified live on macOS (`pmset -g` confirmation, real process-death auto-release) rather than only mocked; and the bugs found during that testing documented with root causes in the repo instead of quietly fixed.

None of this makes the software magically safe — open source is auditability, not a security guarantee. But it changes the question from "do you trust us?" to "here are 140 lines; see for yourself." For a daemon that runs as root on your machine, that's the only version of the question worth answering.

## Audit It Yourself

```bash
git clone https://github.com/rjmorales13/6ix9ine.git
less 6ix9ine/bin/helper.py        # the entire privileged surface
less 6ix9ine/bin/session_registry.py  # the reference counter
```

Start with `helper.py` — it's the component that matters. If what you find doesn't match what this post claims, [open an issue](https://github.com/rjmorales13/6ix9ine/issues/new); that's what the model is for.
