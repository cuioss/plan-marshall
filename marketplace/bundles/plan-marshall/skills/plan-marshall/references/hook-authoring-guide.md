# Hook Authoring Guide

Canonical contract for plan-marshall scripts invoked as Claude Code hooks. Read this before adding a new hook-driven script or modifying an existing one; the post-2.1.139 delivery channel is JSON-on-stdout, and the silent-fallback failure mode (hook exits 0, terminal sees nothing) recurs whenever authors assume a clean exit is proof of working delivery.

## Hook output contract

Claude Code 2.1.141+ delivers terminal-mutating escape sequences from hook subprocesses through a JSON envelope written to stdout. The host parser reads the envelope and forwards the contained escape sequence to the controlling terminal on the script's behalf. Hook subprocesses cannot reach the user's terminal by any other channel.

| Invocation mode | Expected stdout payload |
|-----------------|-------------------------|
| Hook (any of `SessionStart`, `UserPromptSubmit`, `Notification`, `PostToolUse`, `Stop`, …) | A single JSON object: `{"terminalSequence": "<OSC>"}` where `<OSC>` is the escape sequence (e.g. `\x1b]0;title\x07`). Emit nothing — neither stdout nor stderr — when the hook has nothing to render. |
| `--statusline` (Claude Code's `statusLine` command) | Plain text written verbatim to stdout. Claude Code prints it to the statusline without further parsing. No JSON envelope. |

The two modes share a script entry point in practice but differ in payload format. Branch on the invocation mode (typically a `--statusline` flag) and emit exactly one shape per branch.

## Why pre-2.1.139 hooks silently break on upgrade

Before Claude Code 2.1.139, hook subprocesses could open `/dev/tty` and write escape sequences directly to the controlling terminal. The 2.1.139 release removed `/dev/tty` access for hook subprocesses; opening it now fails with an OS-level error. Hooks written against the old contract typically wrap the `/dev/tty` write in a broad `except` clause so a missing or unwritable TTY does not break the user's session. Post-upgrade, that same defensive `except` swallows every write attempt — the hook exits 0 with no stderr, Claude Code records a successful hook invocation, and the terminal sees no change. The failure is silent at every layer.

The JSON envelope contract makes the regression observable: Claude Code parses stdout and surfaces malformed envelopes, and `terminalSequence` is the only delivery channel the host honours. A hook that does not emit a valid envelope cannot mutate the terminal, period.

## Three-step sanity-check workflow

Use this whenever you add or modify a hook-driven script. Each step targets one layer of the delivery chain; running the chain end-to-end is the only way to confirm working delivery.

1. **Invoke the script directly with a representative hook stdin payload.** Pipe the JSON the host would normally provide (event name, session id, prompt, cwd, etc.) into the script and capture stdout. The script should produce a JSON object with a `terminalSequence` field — or no output at all when the hook chose not to render. Anything else (a raw escape sequence on stdout, output on stderr, a non-zero exit) is a contract violation.

2. **Inspect the stdout envelope.** Confirm the JSON parses, the top-level key is `terminalSequence`, and the value is the exact escape sequence you intend the terminal to render. A mis-spelled key (`terminal_sequence`, `terminalSeq`) is the most common envelope failure and produces the silent-fallback symptom — Claude Code drops the payload without warning.

3. **Restart Claude Code and observe the live terminal/statusline.** The host parses envelopes only inside a real Claude Code session, so a passing direct invocation is necessary but not sufficient. Re-launch Claude Code (the hook config is read at session start), trigger the event the hook listens to, and verify the title/statusline updates. This is the step authors most commonly skip; without it, the silent-fallback symptom remains undetected.

## Anti-pattern: "exit 0 with no stderr" is not proof of working delivery

The defining symptom of the post-2.1.139 regression is that the failing code path produces a normal-looking trace: the hook script exits 0, writes nothing to stderr, and Claude Code records the invocation as successful. The trace is identical to a working hook that simply chose not to render. Authors who verify hooks by re-running them and confirming a clean exit miss the bug entirely.

Treat exit code and stderr as necessary but insufficient evidence. The terminal mutation itself — observed after a Claude Code restart, in a real session — is the only acceptance signal. The three-step sanity-check workflow above is structured around that signal precisely because exit-code-based verification is unreliable for this class of script.

## Worked example

The `plan-marshall:platform-runtime` skill provides the canonical hook-driven implementation for this repository. The `SessionStart` hook calls `session capture` (which reads `$CLAUDE_CODE_SESSION_ID` and stores it in `status.json`), and the `UserPromptSubmit` pre-prompt JS calls `session render-title` (which reads `title-body.txt` and emits the OSC title sequence). Both are built on top of the contract described here.
