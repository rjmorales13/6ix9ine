# How to record the 6ix9ine demo GIF

Goal: a short (~8–12 second) looping GIF showing the `t69` dashboard flip from
**IDLE / 💤 SLEEP AVAILABLE** → **ACTIVE / 🚫 SLEEP BLOCKED** → back to idle,
driven by a session starting and ending. This is the single highest-impact
asset for the README and every social post.

You do NOT need to physically close your laptop lid for the demo. Running
`6ix9ine acquire` / `6ix9ine release` makes the dashboard flip on camera, which
is exactly the visual we want to show.

---

## One-time setup (install the converter)

macOS records screen to `.mov`. We convert that to a high-quality GIF with
`gifski` (best-in-class GIF encoder, one command to install):

```bash
brew install gifski
```

That's the only install. Screen recording itself is built into macOS.

---

## The recording — step by step

### 1. Arrange two terminal windows side by side

- **Window A (the star):** make it reasonably large, then run the dashboard:

  ```bash
  t69
  ```

  Leave it showing the **idle** state (no active sessions, `💤 SLEEP AVAILABLE`).

- **Window B (off to the side, you'll type here):** this is where you'll fire
  the acquire/release commands. You can keep it small — it does NOT need to be
  in the recording frame.

### 2. Rehearse the beats once without recording

The story you're capturing, in order:

1. Dashboard sitting **idle** (2 sec)
2. A session appears → status flips to **ACTIVE / 🚫 SLEEP BLOCKED** (hold 3–4 sec)
3. Session ends → status flips back to **IDLE / 💤 SLEEP AVAILABLE** (hold 2 sec)

In Window B, the two commands that drive it:

```bash
# make a session appear (dashboard flips to ACTIVE / SLEEP BLOCKED)
6ix9ine acquire --agent claude --reason "overnight refactor"

# ...wait a few seconds so it's clearly on screen...

# end the session (dashboard flips back to IDLE / SLEEP AVAILABLE)
6ix9ine release --agent claude --reason "overnight refactor"
```

> If your CLI's `acquire`/`release` flags differ, run `6ix9ine acquire --help`
> first and adjust. The point is just: one command makes a session start, one
> makes it end.

### 3. Start the screen recording

- Press **⌘ + Shift + 5**. The macOS screen-capture toolbar appears.
- Click **"Record Selected Portion"** and drag a box **tightly around Window A**
  (the dashboard only — crop out desktop clutter and Window B).
- Click **Record**.

### 4. Perform the beats

1. Let it sit idle ~2 seconds.
2. Switch to Window B, run the `acquire` command, switch back — watch it flip to
   **ACTIVE / 🚫 SLEEP BLOCKED**. Hold ~3–4 seconds.
3. Run the `release` command — watch it flip back to **IDLE / 💤 SLEEP AVAILABLE**.
   Hold ~2 seconds.

### 5. Stop the recording

- Click the **stop icon** in the menu bar (top-right), or press **⌘ + Ctrl + Esc**.
- A thumbnail flashes in the bottom-right; the `.mov` saves to your **Desktop**
  by default (named like `Screen Recording 2026-…​.mov`).

---

## Convert the .mov to a GIF

Move the recording somewhere easy and convert it. From the repo root:

```bash
# rename the recording to something simple first (adjust the path to yours)
mv ~/Desktop/Screen\ Recording*.mov ~/Desktop/demo.mov

# convert → GIF, scaled to 900px wide, 18 fps, high quality, into the repo
gifski ~/Desktop/demo.mov --width 900 --fps 18 --quality 90 -o docs/demo.gif
```

Check the result:

```bash
open docs/demo.gif
```

Aim for a file **under ~4 MB** so GitHub loads it fast. If it's too big, lower
the width (`--width 720`) or fps (`--fps 12`) and re-run.

---

## Drop it into the README

The README already has a marked slot near the top. Find this block:

```
<!--
  DEMO GIF SLOT — ...
-->
![6ix9ine dashboard — live view](docs/dashboard-full.svg)
```

Change that image line to:

```
![6ix9ine in action](docs/demo.gif)
```

Tell me when `docs/demo.gif` exists and I'll do this swap + commit for you — or
you can make the one-line edit yourself.

---

## Reuse it everywhere

Same GIF is the hero for:
- The README (top slot)
- The Twitter/X hero tweet (attach the GIF directly — native video/GIF beats a code screenshot)
- Reddit r/macOS and r/ClaudeAI posts (embed it)
- Product Hunt gallery

One recording, every channel.
