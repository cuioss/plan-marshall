# Menu Option: Enforcement Hook

Configure the conditional PreToolUse enforcement hook. When enabled, the hook
deterministically blocks four mechanically-checkable hard-rule violation
families — shell-construct compounds, Bash file-ops, direct edits of the
generated `.plan/execute-script.py`, and hard-coded build commands
— but ONLY when the call originates inside a plan-marshall plan context (a
dispatched execution-context sub-agent, or a working directory under
`.plan/local/worktrees/`). Every other call passes through untouched: the hook
fails open everywhere outside a satisfied context gate plus a matched rule.

The enforcement opt-in is **independent of the terminal-title wiring** — a
project may enable enforcement without the terminal title, and vice versa. The
install adds only the matcher-less PreToolUse enforcement entry to
`.claude/settings.local.json`; it never touches the terminal-title render,
statusLine, or env entries.

See
[`../../platform-runtime/standards/pretooluse-enforcement.md`](../../platform-runtime/standards/pretooluse-enforcement.md)
for the canonical contract — the context gate, the four rule families with
their redirect reasons, and the fail-open / best-effort-no-raise behaviour.

## Reachability

This option is reachable from the marshall-steward **Configuration** menu
(Main Menu → "3. Configuration" → "Enforcement Hook"), regardless of whether
the project is being set up for the first time or is already configured.

---

## Detect → Confirm → Install

The flow mirrors the terminal-title Action A
([`menu-terminal-title.md`](menu-terminal-title.md) § Action A): a non-mutating
probe via `health-check --checks display`, an `AskUserQuestion` confirmation,
then a convergent `project install-hook --enforcement` install — one that never
duplicates an entry and brings an already-present one onto the current shape.

### Step 1: Detect

Probe the enforcement entry's `present` / `divergence` / `MISSING` state via the
platform-runtime health-check `display` surface. That surface reads BOTH
`.claude/settings.json` and `.claude/settings.local.json`: an entry in either
file alone counts as `present`, and an entry in both reads `divergence`, so the
probe scope is the pair rather than the local file the install writes:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  health-check --checks display
```

Inspect the `display` entry in the `results` array. Its `detail` field reports
every required surface on its own line; scan for the dedicated
`PreToolUse:enforcement` line:

- `PreToolUse:enforcement: present` — the enforcement entry is installed in
  exactly one of the two settings files. **Presence is not correctness**: the
  `display` check keys on the hook command string alone and never inspects the
  entry's `timeout`, so a present entry can still carry a stale one. A re-run of
  the install converges such an entry when it lives in the file the install
  writes, so offer it — with the caveat below — rather than returning silently:

  ```text
  The PreToolUse enforcement hook is already configured.

  The enforcement entry is present in the Claude settings. The probe reads both
  ./.claude/settings.json and ./.claude/settings.local.json and reports only
  that exactly one of them carries the entry, never which one. A fresh Claude
  Code session arms the hook automatically either way.

  The presence check does not inspect the hook timeout, so a present entry may
  still carry a stale one. The install writes ./.claude/settings.local.json, so
  re-running it converges a stale timeout only for an entry that lives there; an
  entry already correct is left untouched and the file is not written at all.
  An entry that lives in ./.claude/settings.json instead is not reached: the
  re-run appends a second entry to ./.claude/settings.local.json and leaves the
  install dual-homed — the `divergence` state described below, which nothing
  here repairs.
  ```

  ```text
  AskUserQuestion:
    question: "The enforcement hook is already installed, but the check that found it does not read the hook's timeout, and it cannot tell which of the two settings files holds the entry. A re-run fixes an out-of-range timeout in ./.claude/settings.local.json, and adds a duplicate if the entry actually lives in the shared ./.claude/settings.json. Re-run the install?"
    header: "Enforcement Hook"
    options:
      - label: "Re-run install"
        description: "Rewrites the hook timeout only if it falls outside the plausible seconds range and the entry lives in ./.claude/settings.local.json; an entry in the shared ./.claude/settings.json is not converged, and a second copy is added alongside it, leaving the install dual-homed"
      - label: "Leave as is"
        description: "Make no changes and return to the Configuration menu; the hook stays armed with whatever timeout it carries, and no duplicate can be created"
    multiSelect: false
  ```

  On **Leave as is**: write nothing and return to the Configuration menu. The
  detect probe above is non-mutating, so declining leaves the settings file
  exactly as found.

  On **Re-run install**: proceed to Step 3 (Install), skipping the Step 2
  enable prompt — the user has already consented to this write. Expect
  `enforcement_status: migrated` when a stale value was rewritten,
  `already_present` when the entry was already correct, or `installed` when the
  present entry lived in the shared file and this call added a second one to
  ./.claude/settings.local.json. `enforcement_status` is what distinguishes the
  three — `settings_path` names the file the install wrote and is the same in
  all three cases.

- `PreToolUse:enforcement: divergence` — the enforcement entry is installed in
  BOTH `.claude/settings.json` and `.claude/settings.local.json`. The entry IS
  installed, so this is **report-only** and is **NOT** a reason to offer the
  install prompt. Report the observation and change nothing:

  ```text
  The PreToolUse enforcement hook is already configured, in both settings files.

  The enforcement entry is present in ./.claude/settings.json AND in
  ./.claude/settings.local.json. This is reported for your awareness only —
  nothing here repairs, migrates, or de-duplicates it, and the hook is armed
  either way.
  ```

  Return to the Configuration menu. Do NOT proceed to Step 2, and do NOT offer
  the re-run install: this flow writes only `.claude/settings.local.json`, so it
  cannot resolve a state that spans both files, and offering a write that cannot
  change the reported condition would be misleading.

- `PreToolUse:enforcement: MISSING` — the enforcement hook is not installed.
  Proceed to Step 2.

Note: the enforcement entry is orthogonal — a `MISSING` enforcement line does
NOT make the terminal-title `display` check unhealthy, a `divergence` line
likewise does NOT make it unhealthy (it reports an installed entry), and a
`present` enforcement line does not by itself make it healthy. Read the
`PreToolUse:enforcement` line specifically, not the overall `healthy` flag.

### Step 2: Confirm

Prompt the user before writing anything:

```text
AskUserQuestion:
  question: "Enable the conditional PreToolUse enforcement hook? It deterministically blocks four hard-rule violation families (shell-construct compounds, Bash file-ops, generated-executor edits, hard-coded builds) inside a plan-marshall plan context, and fails open everywhere else. This installs ONLY the enforcement entry into ./.claude/settings.local.json — it does not touch the terminal-title wiring."
  header: "Enforcement Hook"
  options:
    - label: "Enable"
      description: "Install the matcher-less PreToolUse enforcement entry (orthogonal to the terminal-title bundle)"
    - label: "Skip"
      description: "Make no changes; enforcement stays disabled"
  multiSelect: false
```

On **Skip**: write nothing and return to the Configuration menu.

On **Enable**: proceed to Step 3.

### Step 3: Install

Install the enforcement entry via `project install-hook --enforcement`:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  project install-hook --target claude --enforcement
```

Inspect the TOON response:

- `status: success` — the call landed. Read `enforcement_status`:
  - `installed` — the enforcement entry was freshly added.
  - `migrated` — the entry was already there but carried a stale `timeout`,
    which this call rewrote to the current value.
  - `already_present` — the entry was already there and already correct (no
    write needed).
- `status: error` — report the `message` field and advise the user to check
  write permissions on `./.claude/settings.local.json`.

The top-level `already_present` field is True only for the third case: a run
that installed or converged anything reports `false`.

#### Final report

```text
PreToolUse enforcement hook enabled.

Enforcement entry: <enforcement_status>

Restart or reload the Claude Code session so the harness arms the hook. The
hook blocks the four hard-rule families only inside a plan-marshall plan
context; calls outside any plan pass through untouched. Enforcement is
independent of the terminal-title wiring — enabling one does not enable the
other.
```

After completion, return to the Configuration menu.
