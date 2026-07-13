# macOS Compatibility Matrix

This document details the support status, known issues, and limitations of **6ix9ine** across different macOS versions and hardware configurations.

## Minimum System Requirements

*   **Operating System**: macOS 14.0 (Sonoma) or newer.
*   **Python**: Python 3.13+ (or self-contained standalone binary release).
*   **Privileges**: Administrator rights (only required for setting up the privileged root sleep helper).

---

## macOS Version Support Matrix

| macOS Version | Codename | Support Status | Notes / Limitations |
| :--- | :--- | :--- | :--- |
| **macOS 15.x** | Sequoia | ✅ **Fully Supported** | Tested end-to-end. Full compatibility with TUI dashboard, daemon, and privileged helper. |
| **macOS 14.x** | Sonoma | ✅ **Fully Supported** | Tested end-to-end (Target Platform). High-fidelity sleep blocking and clamshell detection. |
| **macOS 13.x** | Ventura | ⚠️ **Partial Support** | Daemon works, but `launchctl` behavior differences may require manually running the CLI commands under some user configurations. |
| **macOS 12.x** | Monterey | ❌ **Unsupported** | Lack of support for some modern Unix socket credentials lookup APIs (`LOCAL_PEERPID`). |
| **macOS 11.x** | Big Sur | ❌ **Unsupported** | Legacy launchctl interface compatibility issues and python library compilation conflicts. |
| **macOS 10.15** | Catalina | ❌ **Unsupported** | Unsupported by core dependencies. The text-based user interface (Textual) requires modern terminal capabilities. |

---

## Core Features & Hardware Configurations

### 1. Clamshell Mode (Lid Closed)
*   **Status**: ✅ **Fully Supported**
*   **Details**: When a Mac is connected to power and an external display (docked), closing the lid normally triggers sleep. 6ix9ine's root-privileged helper invokes `pmset disablesleep 1` to override this behavior, allowing your background agents to continue processing tasks overnight with the lid closed.
*   **Lid State Detection**: The background daemon monitors lid close/open events. Opening the lid prints a session log summary to the CLI and TUI.

### 2. External Displays
*   **Status**: ✅ **Fully Supported**
*   **Details**: 6ix9ine manages system-level sleep assertions rather than display sleep assertions. Your external display will still dim and turn off to conserve energy according to your macOS Energy Saver preferences, but the underlying system CPU, network stack, and running agents (Claude Code, OpenCode, Docker, etc.) will remain fully active and awake.

### 3. Thermal Safe Cutout
*   **Status**: ✅ **Fully Supported**
*   **Details**: To prevent hardware damage on docked Macs (especially inside bags or under high workloads with closed lids), 6ix9ine constantly monitors CPU temperature. If the temperature exceeds the configured threshold (default `85°C`), the daemon automatically releases all sleep blocks and restores system sleep capabilities.

---

## Known Limitations

1.  **Rosetta 2 Emulation**: Running 6ix9ine under Rosetta 2 emulation on Apple Silicon Macs is not recommended. The privileged helper socket authentication relies on accurate PID/UID resolution, which can be misreported under emulation. Always use native binaries (`arm64` on Apple Silicon or `x86_64` on Intel).
2.  **Fast User Switching**: Sleep-blocking assertions are system-wide. If multiple local user accounts are active, the background daemon running under the active session controls the system sleep block.
