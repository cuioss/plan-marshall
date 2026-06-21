# Menu Option: Enforcement Hook

Configure the conditional PreToolUse enforcement hook. When enabled, the hook
deterministically blocks five mechanically-checkable hard-rule violation
families — shell-construct compounds, Bash file-ops, direct `gh`/`glab`, direct
edits of the generated `.plan/execute-script.py`, and hard-coded build commands
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
for the canonical contract — the context gate, the five rule families with
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
then an idempotent `project install-hook --enforcement` install.

### Step 1: Detect

Probe the current `.claude/settings.local.json` for the enforcement entry's
present/MISSING state via the platform-runtime health-check `display` surface:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  health-check --checks display
```

Inspect the `display` entry in the `results` array. Its `detail` field reports
every required surface on its own line; scan for the dedicated
`PreToolUse:enforcement` line:

- `PreToolUse:enforcement: present` — the enforcement hook is already installed.
  Print an "already configured" message and return to the Configuration menu
  WITHOUT prompting:

  ```
  The PreToolUse enforcement hook is already configured.

  The enforcement entry is present in ./.claude/settings.local.json. A fresh
  Claude Code session arms the hook automatically.
  ```

- `PreToolUse:enforcement: MISSING` — the enforcement hook is not installed.
  Proceed to Step 2.

Note: the enforcement entry is orthogonal — a `MISSING` enforcement line does
NOT make the terminal-title `display` check unhealthy, and a `present`
enforcement line does not by itself make it healthy. Read the
`PreToolUse:enforcement` line specifically, not the overall `healthy` flag.

### Step 2: Confirm

Prompt the user before writing anything:

```
AskUserQuestion:
  question: "Enable the conditional PreToolUse enforcement hook? It deterministically blocks five hard-rule violation families (shell-construct compounds, Bash file-ops, direct gh/glab, generated-executor edits, hard-coded builds) inside a plan-marshall plan context, and fails open everywhere else. This installs ONLY the enforcement entry into ./.claude/settings.local.json — it does not touch the terminal-title wiring."
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
  project install-hook --target .claude/settings.local.json --enforcement
```

Inspect the TOON response:

- `status: success` — the call landed. Read `enforcement_status`:
  - `installed` — the enforcement entry was freshly added.
  - `already_present` — the entry was already there (no write needed).
- `status: error` — report the `message` field and advise the user to check
  write permissions on `./.claude/settings.local.json`.

#### Final report

```
PreToolUse enforcement hook enabled.

Enforcement entry: <enforcement_status>

Restart or reload the Claude Code session so the harness arms the hook. The
hook blocks the five hard-rule families only inside a plan-marshall plan
context; calls outside any plan pass through untouched. Enforcement is
independent of the terminal-title wiring — enabling one does not enable the
other.
```

After completion, return to the Configuration menu.
