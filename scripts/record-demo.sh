#!/usr/bin/env bash
set -euo pipefail

# Records the t69 dashboard flip (idle -> active -> idle) as a .mov,
# then converts it to a GIF for docs/demo.gif.
#
# Usage: ./scripts/record-demo.sh
#
# This script ONLY handles screen recording + GIF conversion. It does NOT
# call `6ix9ine acquire`/`release` itself — the acquire/release hooks are
# already installed for claude/opencode, so simply typing a prompt into
# either agent's terminal during the recording window will trigger a real
# ACTIVE session automatically. To capture the full idle -> active -> idle
# loop in ~15 seconds:
#
#   1. Run this script.
#   2. Have a "sleep 7" (or similar ~7 second) command pre-typed but NOT
#      yet submitted in both the claude and opencode terminals.
#   3. During the 3-second countdown, make sure your windows (t69, claude,
#      opencode) are arranged and visible.
#   4. Once recording starts: after ~2-3 sec, hit Enter on both terminals.
#   5. Watch t69 flip to ACTIVE / SLEEP BLOCKED, hold for ~7 sec while the
#      sleep runs, then let it finish naturally — no Ctrl+C needed. The
#      release hook fires automatically on completion, flipping the
#      dashboard back to IDLE / SLEEP AVAILABLE.
#   6. Let the recording finish (auto-stops after DURATION seconds).

REGION="0,40,1742,1129"   # x,y,w,h — bounding box of the 3 terminal windows
OUT_MOV="$HOME/Desktop/6ix9ine-demo.mov"
OUT_GIF="docs/demo.gif"
DURATION=15                # total seconds to record

rm -f "$OUT_MOV"

echo "Recording will start in 3 seconds. Region: $REGION"
echo "Plan: idle (~2-3s) -> prompt agent -> hold ACTIVE (~3-4s) -> Ctrl+C agent -> idle -> stop"
sleep 3

screencapture -V "$DURATION" -R "$REGION" "$OUT_MOV"

echo "Recording saved to $OUT_MOV"
echo "Converting to GIF..."

gifski "$OUT_MOV" --width 900 --fps 18 --quality 90 -o "$OUT_GIF"

echo "Done. GIF saved to $OUT_GIF"
ls -la "$OUT_GIF"
open "$OUT_GIF"
