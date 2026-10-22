# PreToolUse Enforcement Hook

The PreToolUse enforcement hook deterministically blocks six
mechanically-checkable hard-rule violation families. Rules **R1–R5** apply when
the call originates inside a plan-marshall plan context, when the checkout
carries a live runbook-lane marker, **or in every session of the plan-marshall
source repository**; **R6 is not context-gated at all** (only its unresolvable
fail-closed branch is limited to that scope). This document
is the canonical reference for the hook's context gate, rule families, fail-open
contract, the capture-validates-the-gate dependency chain, and the on-demand
registration model.

## Components

Three scripts in `scripts/` implement the hook, layered shared-gate-first:

| Script | Role |
|--------|------|
| `pretooluse_gate.py` | Shared, pure-function library: the SINGLE home of payload-field knowledge and the context-gate predicate. Imported by both leaves; owns NO rule matchers. |
| `claude_pretooluse_capture.py` | Observe-only leaf that imports the shared gate and records the raw payload + the gate's extracted fields + would-be verdict. Always exits 0 emitting nothing. Used to validate the gate's field names against real payloads before enforcement is armed. |
| `claude_pretooluse_hook.py` | Enforcement leaf that imports the SAME shared gate and adds ONLY the R1–R6 rule matchers + the `permissionDecision: deny` envelope on top. |

The dependency ordering is **shared-gate (best-guess) → capture (validate /
correct) → enforce (final)**: the shared gate's best-guess field names are
authored first, the capture run confirms or corrects them against the empirical
PreToolUse payload schema, and only then is the enforcement leaf finalized on
top of the validated shared gate. No field-name knowledge is duplicated across
the two leaves — all of it lives in `pretooluse_gate.py`.

## Scope — the three signals, the repository marker and the two harnesses

Two harnesses enforce the same decision table: the **Claude PreToolUse hook**
(`claude_pretooluse_hook.py`) and the **OpenCode guard** (`.opencode/plugin/
guard.js`). On the Claude hook, R1–R5 bind when ANY of the following fires; the
OpenCode guard applies R1–R4 unconditionally and gates only R5 on the same
predicate. **R6 is not context-gated on either harness** (only its unresolvable
fail-closed branch is limited to that scope).

- **Signal 1 — sub-agent identity.** The sub-agent identity field carries the
  `:execution-context` marker (the call runs inside a dispatched
  execution-context sub-agent). The identity value is bundle-qualified — e.g.
  `plan-marshall:execution-context-level-4` (and
  `plan-marshall:execution-context-reader-level-N` for readers) — so the gate
  matches the `:execution-context` substring, NOT a bare prefix. The field name
  and marker were confirmed against real PreToolUse payloads by the capture run.
- **Signal 2 — worktree cwd.** The working directory resolves under
  `.plan/local/worktrees/` (the call runs inside a plan worktree).
- **Signal 3 — runbook-lane marker (the 24-hour lane marker).** A
  `.plan/temp/rb-<plan>/progress.md` file exists in the project directory and was
  modified within the last 24 hours. A lane run issues every call with the main
  checkout as its working directory, so neither Signal 1 nor Signal 2 fires
  there and a consumer repository would otherwise be left unbound.

  **Decision — the whole-checkout, 24-hour scope is intended.** The payload
  carries no lane-run identity that would separate the lane's own session from
  another session in the same checkout, so a per-session narrowing is not
  decidable from the fields the gate reads; the marker is written only by a
  runbook-lane run, which makes "this checkout is running a lane" the narrowest
  scope the payload can express. The freshness bound is what keeps a PAST lane
  run from binding the checkout forever, and it is the part that was missing
  before PLAN-LB-79. Narrowing further would require the lane to record its
  session id in the marker, which is a change to the lane contract, not to this
  gate.
- **Repository marker.** The project directory carries the plan-marshall source
  repository's own copy of the shared allow-list
  (`marketplace/bundles/plan-marshall/skills/platform-runtime/standards/
  r5-allowlist.json`). A root session of this repository is therefore bound with
  no sub-agent identity and no worktree cwd — the state PLAN-LB-79 D3 closed.

An absent Signal-1 field still lets Signal 2 satisfy the gate, and vice versa.

| Scope input | Claude PreToolUse hook | OpenCode guard |
|-------------|------------------------|----------------|
| Signal 1 | the `agent_type` value carrying `:execution-context` | the `agent` value carrying `:execution-context` |
| Signal 2 | the payload `cwd` under `.plan/local/worktrees/` | the shell `workdir`, falling back to the project root, under `.plan/local/worktrees/` |
| Signal 3 (24-hour lane marker) | `.plan/temp/rb-<plan>/progress.md` under `CLAUDE_PROJECT_DIR`, falling back to the payload `cwd`, fresh within 24 h | the same marker under the guard's project root, fresh within 24 h |
| Repository marker | `CLAUDE_PROJECT_DIR`, falling back to the payload `cwd`, then to the hook's own location, carries the shared allow-list file | the guard's project root carries the same file |
| R6 | unconditional | unconditional |

Both harnesses therefore bind a root session of this repository. On the Claude
hook a consumer repository outside a plan context is refused nothing except R6.
The OpenCode guard applies R1, R2, R3, R4 and R6 unconditionally, so a consumer
project that installs that guard IS bound by those rules; only its R5 is gated.

## Rule families

The R1–R6 matchers are enforcement-only — they live solely in the enforcement
leaf, layered on top of the shared gate, and run against the shared gate's
`tool_name(payload)` / `tool_input(payload)` accessors. When the gate is satisfied
OR this project IS the plan-marshall source repository the leaf runs R1–R5; R6
runs unconditionally. On the first matching
rule the leaf appends one `guard.log` audit
line (best-effort) and emits a `permissionDecision: deny` envelope carrying a
one-line `permissionDecisionReason`; on no match it emits nothing.

| Rule | Fires on | Redirect reason (substance) |
|------|----------|-----------------------------|
| **R1 shell-construct compound** | A Bash command containing an **unquoted, unescaped** `&&`, `;`, `\|`, `&`, newline, `for`/`while` loop, `$(...)` command substitution, or leading `VAR=val cmd` inline env-var assignment. Quoting and backslash escapes are resolved first, so an operator confined to a quoted argument is data and does not fire — but a `$(...)` or backtick substitution still fires inside **double** quotes, where the shell still executes it | One command per Bash call — use separate Bash calls or dedicated tools |
| **R2 Bash file-ops** | A Bash command whose program is `cat` / `grep` / `head` / `tail` / `find` / `ls`, a **shell spawn** (the shared wrapper table's `shells` plus the `source` builtin — the spawn set is DERIVED from that table, so neither implementation carries a second literal shell list), **or** `git` whose subcommand (after any global options) is `grep` | Use the Read/Glob/Grep tools, not Bash, for file operations; for a content sweep run `architecture search --content --pattern P` |
| **R3 generated-executor edit** | An Edit/Write whose path is the generated `.plan/execute-script.py` | Regenerate the executor via `/sync-harnesses` + `/marshall-steward`; never edit it |
| **R4 hard-coded build** | A Bash command invoking `./pw` or a bare `mvn` / `npm` / `gradle` / `uv` (the program is read un-stripped and after R5 wrapper stripping, so `env uv run python -c ...` is refused). The `./pw` verdict is the shared table's `build_wrapper_admission` (`generate*` and `--*` admitted today), so the hook and the guard give `./pw generate` — the command `CLAUDE.md` prescribes — ONE verdict | Resolve build commands via `plan-marshall:manage-architecture:architecture resolve` |
| **R5 direct interpreter call** | A Bash command invoking an interpreter (`python` / `python3` / `pypy` / `pypy3` / a versioned spelling such as `python3.12`, case-insensitively) as `-c`, a script path, a bare `-` (STDIN) or a `-<`/`->` redirection, or `-m` with any module — except the executor permit (the relative `python3 .plan/execute-script.py` run from the repository root, or an absolute form equal to `{repository root}/.plan/execute-script.py` after path normalization) and the shared allow-list of documented non-executor invocations. **R5 binds inside a plan context, in a live runbook-lane run, AND in every session of the plan-marshall source repository.** The wrapper prefixes come from ONE shared data file, [`r5-wrappers.json`](r5-wrappers.json): a path-qualified `/usr/bin/env` strips like `env`, an option cluster like `env -iu FOO` is walked letter by letter, `timeout` / `flock` / `chrt` / `taskset` consume their leading positional, `env -S` and a shell's `-c` splice the command string back into the walk (all of its segments), `watch`/`parallel` splice their positional command string, and `find … -exec` is walked from the program it runs. A shell's `cd` inside the spliced string is applied in order, so the executor is judged from the directory it really runs in. The **fail-closed floor** runs before R2: a wrapper handed a command string, stdin (a here-string or here-document) or a SCRIPT FILE is refused when that text names an interpreter ANYWHERE, so a grouping keyword (`if`/`then`/`for`/`case`/`{ }`/`( )`/`!`), a shell option before `-c`, a here-string or a script file cannot hide the call; the segment walk decides only whether the text is the admitted executor. With the table absent the check reads each raw token's own content, so `zsh -c "python3 -c x"` is refused rather than read as an opaque token | Route builds and checks via `python3 .plan/execute-script.py`; `.plan` state via `manage-*` verbs or the Read/Edit/Write tools |
| **R6 raw finalize commit** | A raw `git commit` while the enclosing plan — NAMED from every commit form: the `--work-tree` value, the composed `git -C` target, the plan a `--git-dir` / `GIT_DIR` admin directory points at (`…/worktrees/{plan}`), then the shell workdir, then the project root — its `status.json` field `current_phase` read from the WORKTREE-RESIDENT record first (the live one during phase 5+) and the main-anchored record otherwise, never "the first plan found". A subcommand defined with `-c alias.NAME=…` is resolved to its body; a shell-expansion alias body and any directory value that still carries an unexpanded variable are UNRESOLVABLE and refused fail-closed. **R6 is not context-gated.** Every plan commit must pass through the gate-bearing `git-workflow commit` verb, which sanctions an open loop-back fix task, a review-rubric section-6 record, or a step id of the plan's composed phase-6 manifest. R6 runs after R1 and BEFORE R2–R5 on both harnesses, so the shell-spawn class cannot shadow the specific raw-commit rule for a commit wrapped in a shell string (the interpreter floor still takes precedence, which is the more severe refusal) | Commit via `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow commit` |

### R5 — allow-list, wrappers, and the audit line

R5 refuses the interpreter side door while leaving the repository's own
documented workflows runnable. Three things make that split explicit:

- **Allow-list.** One declared data file,
  [`r5-allowlist.json`](r5-allowlist.json), names the documented non-executor
  invocations R5 permits (the harness sync engine, the stewards' bootstrap
  scripts, and the executor generator). The Claude hook and the OpenCode guard
  plugin read the SAME file, so the two decision tables agree. Its `entries` are
  REPOSITORY-RELATIVE paths, matched EXACTLY against the invocation's script path
  resolved against the repository root; its `bundle_entries` are BUNDLE-RELATIVE
  paths, matched EXACTLY against `{deployed bundle root}/{entry}` for the
  platform-runtime bundle-cache layout (the nested Claude plugin cache and the
  flat OpenCode / Antigravity skill roots). Neither form is ever a basename and
  never a suffix, so a copy of an allow-listed script outside the repository, or
  under a non-deployed directory, never matches. A RELATIVE
  token is joined with the shell's working directory FIRST, so a same-named script
  under a different cwd resolves outside the repository and is refused; the root
  is the project directory (the guard's `ctx.location.directory`; the hook's
  `CLAUDE_PROJECT_DIR`, falling back to the hook's OWN location — never the
  payload `cwd`). When the file is absent the hook
  uses a narrow built-in base table (`marketplace/targets/sync.py`); the executor
  permit is hardcoded separately.

  **Decision — the unversioned `{root}/plan-marshall/{entry}` candidate stays
  accepted.** The deployed-form match builds three spellings from a
  resolver-named root: the flat skill directory, the nested `{root}/{bundle}/
  {entry}`, and the newest VERSION directory under it. The unversioned form is a
  real install shape (an operator who unpacks a bundle without a version
  directory), it is still under a root the layout names, and it is compared by
  EXACT realpath equality — so keeping it admits only a path inside a deploy root
  the resolver already trusts, and never widens the trusted set. Removing it
  would refuse that install shape for no security gain, so it stays.
- **Wrappers and versioned interpreters.** A prefix cannot hide the interpreter.
  The wrapper population is ONE shared data file,
  [`r5-wrappers.json`](r5-wrappers.json), read by the Claude hook, the OpenCode
  guard plugin and the enforcement pins — neither implementation carries a second
  literal list. A wrapper is matched by BASENAME (`/usr/bin/env` strips like
  `env`); its value-consuming options, its short-option clusters (`env -iu FOO`),
  its leading positional arguments (`timeout`'s duration, `flock`'s lock file,
  `chrt`'s priority, `taskset`'s mask) and its command-string options
  (`env -S`/`--split-string`, a shell's `-c`, `script -c`) all come from that
  file. The shells (`bash`/`sh`/`dash`/`zsh`/`ksh`/`fish`/`csh`/`tcsh`/`$SHELL`),
  the runners (`ionice`/`chrt`/`taskset`/`flock`/`watch`/`parallel`/`busybox`/
  `script`) and `find … -exec` are all covered, and a versioned spelling
  (`python3.12`) or a `pypy` interpreter is recognised. A wrapper's spliced
  command string is walked SEGMENT BY SEGMENT, so `zsh -c "cd /tmp; python3 -c
  x"`, `env -S "cd /tmp; python3 -c x"` and `watch 'cd /tmp && python3 -c x'`
  are refused too, and a `cd` inside the string is applied to the executor
  admission. What the segment walk does not model is covered by the
  **fail-closed floor**: a wrapper handed a command string, stdin (a here-string
  or here-document) or a script file is refused when that text names an
  interpreter ANYWHERE — a grouping keyword, an option before `-c`, a here-string
  and a script file included — while the walk decides only whether that text is
  the admitted executor. The program token is matched case-insensitively. When
  the data file is unreadable the check fails CLOSED for the interpreter class:
  every raw token's own content is scanned, so `zsh -c "python3 -c x"` is refused
  as well, because no wrapper can be stripped without the table. Because the R2
  shell-spawn set is DERIVED from that same table, a missing table also means no
  TABLE shell is identified there (`source` still is — it is the one builtin the
  set adds) — the mutation class itself (`rm`, `mv`, `cp`, …) is still refused
  directly, and the interpreter class is refused by the scan above; the table is
  what supplies the shell names, so that is the accepted cost of having exactly
  one list.
- **Audit line.** On a refusal the hook appends one line to
  `<cwd>/.plan/temp/guard.log`, in the same shape the OpenCode guard writes:
  `<ISO-8601 millis> | tool=<tool> | rule=<Rn> | session=<session_id> | call=? | <detail>`.
  The `call` field is `?` on Claude, which exposes no tool-call id; the OpenCode
  guard writes the real call id, so the two lines agree on every field Claude
  provides.

### R1 — quoting and escape resolution

A metacharacter that OPERATES and one that is DATA are the same character; only
the quoting tells them apart. R1 therefore scans two masked views of the command
rather than the raw string, because its two marker classes are neutralized by
*different* quoting:

| View | Masks | Why |
|------|-------|-----|
| operator | single- AND double-quoted spans | `&&`, `;`, `&`, a newline, a loop keyword and a leading assignment are inert inside either quote kind |
| substitution | single-quoted spans ONLY | `$(...)` and a backtick stay LIVE inside double quotes — `echo "$(rm -rf /)"` really does substitute, so masking them there would open the bypass the rule exists to prevent |

A **backslash escape is resolved before any quote-state transition**, in
unquoted context and inside a double-quoted span alike; inside a single-quoted
span the shell reads a backslash as an ordinary literal, so the escape is not
applied there. Both the backslash and the character it escapes are masked in
BOTH views, because an escaped character is never an operator and never a
substitution opener. Resolving the escape only inside double quotes was wrong in
both directions at once:

- **Bypass.** In unquoted context an unresolved backslash let the character that
  FOLLOWED it change the span state, so the first command below opened a
  single-quoted span, masked the `;` and closed cleanly — while the shell reads
  the escaped quotes as literal data and the `;` as a live separator, making it
  two commands.
- **False positive.** Copying the raw escaped pair into the substitution view
  left the marker intact there, so the second command below — literal data to
  the shell — denied on the substitution check.

```bash
echo \'a; b\'      # two commands: the ; is live, so R1 must deny
echo "\`date\`"    # one command: the backtick is literal, so R1 must allow
```

One consequence worth naming: an escaped newline is a line **continuation**, so
a command broken across lines with a trailing backslash is a single command and
does not fire the newline check. A bare unquoted newline still does.

**Malformed quoting** — a span that never closes — yields no mask, and every R1
check re-runs against the RAW command. That degradation keeps a lexing ambiguity
a false positive at worst, never a silent bypass.

### R2 — the `git grep` arm

`git grep` reads file bodies exactly as bare `grep` does, so it belongs to the
**existing** R2 family rather than a new one — the family count stays four.

**Predicate**: the command's program is `git` (path prefixes stripped, so
`/usr/bin/git` counts) **and** its subcommand token is `grep`. The subcommand is
resolved by walking past `git`'s global options, because it is not reliably
`tokens[1]`:

The walk is **structural, not an allowlist**: any token starting with `-` is an
option and is skipped. Only the detached value-taking options are named, because
they alone consume a separate following token.

| Global option form | Handling |
|--------------------|----------|
| `-C <path>`, `-c <k=v>`, `--git-dir <path>`, `--work-tree <path>`, `--namespace`, `--super-prefix`, `--config-env`, `--exec-path`, `--attr-source` | Skipped together with the separate value token that follows |
| Any other token starting with `-` — standalone flags (`--no-pager`, `-p`, `--bare`), attached short values (`-C.`, `-cvar=val`), and inline `--option=value` forms | Skipped as one self-contained token |

Testing `tokens[1] == "grep"` directly would be a **vacuous guard**: `git -C . grep x`,
`git -c k=v grep x` and `git --no-pager grep x` all walk straight past it while
performing exactly the content search the rule exists to redirect.

Recognising only a *named set* of option spellings is equally vacuous, and for
the same reason: `git -C. grep x`, `git -cvar=val grep x`, `git -p grep x` and
`git --bare grep x` are all valid `git`, none matches a membership test, and each
would otherwise return its own option token as the subcommand — missing the
`grep` comparison and letting the content search through. The structural
dash-skip is what closes that class, so the option tuple carries no enforcement
weight beyond the detached-value case.

**Decision — the file-search git verbs join the hook's enforced set and stay
outside the guard's.** `git grep` and `git -C … grep` are deliberately not added
to the R5 wrapper table.

Reason: the two surfaces are different classes, and each already reaches a
verdict for the direct spelling. The Claude hook's R2 is the file-ops family, and
its structural option walk refuses `git grep` AND `git -C … grep`. The OpenCode
guard's R2 is the MUTATION class only — read-side probes are governed by the
two-tier permission map — and that map denies the direct `git grep *` spelling at
every tier while a `git -C … grep` command does not match a `git grep *` pattern.
The `git -C …` spelling is therefore recorded as OUTSIDE what the guard enforces:
the guard's R2 is not the place for read-side probes, and adding a wrapper-table
entry would put the verb in the wrong class and create a second, weaker path to a
verdict the hook already reaches. The remedy for a content question is the same on
both harnesses: `architecture search --content --pattern P`. PLAN-LB-79 D1 asked
for this decision and it was never recorded; it is recorded here, and a doc test
asserts this paragraph exists, so it cannot be lost again.

**Explicit non-triggers** — these are not file-ops and must keep working:

- Every non-`grep` git subcommand: `git status`, `git diff`, `git log`,
  `git add`, `git commit`, `git rev-parse`, `git show`, …
- A command whose program merely *contains* `git` (e.g. `gitk`), since the
  program name is compared for equality, not as a substring.
- A `git` invocation whose option walk runs out of tokens before a subcommand
  appears (e.g. a bare `git`) — the walker returns `""`, which never equals
  `grep`, so the call passes through.

**Hot-path cost**: the walk is pure token arithmetic on the already-split command
— no regex compilation at match time, no filesystem access, no subprocess. This
matters because the hook runs on **every** tool call.

## Fail-open / best-effort-no-raise contract

The enforcement leaf fails OPEN on every path outside a matched rule, so a hook
bug can never block the user:

- Empty or malformed stdin → emit nothing, exit 0.
- R1–R5: run when the gate is satisfied OR this project IS the plan-marshall
  source repository; a match → deny, no match → fall through.
- R6: run unconditionally; a match → deny, no match → fall through.
- Neither the gate nor the this-repository scope → emit nothing, exit 0.
- Any internal error → emit nothing, exit 0.

Only an R1–R6 match inside that scope produces a deny. Every accessor in the
shared gate is best-effort and degrades to a safe default rather than raising.

## Verifying the install

The Claude hook is installed **machine-locally**: `project install-hook
--enforcement` writes a matcher-less `hooks.PreToolUse` entry into
`.claude/settings.local.json`, which is git-ignored. The hook is **not installed in this checkout**
(no enforcement entry exists in `.claude/settings.local.json`), and a fresh clone carries no such
file at all — the enforcement a reader gets is whatever that machine's install provides, never a
property of the repository. An operator verifies the binding in three steps:

1. `.claude/settings.local.json` carries a PreToolUse entry whose command runs
   `claude_pretooluse_hook.py` and carries NO `matcher` — a matched entry does not
   enforce on every tool and reads `MISSING` in the diagnostic below.
2. `health-check --checks display` reports `PreToolUse:enforcement: present`
   (the `MISSING` and `divergence` labels name the failure modes).
3. The installed bundle's `standards/r5-wrappers.json` is the table this document
   describes. A stale install whose hook does not carry it fails CLOSED (no
   wrapper can be stripped, so any interpreter is refused) rather than admitting
   a wrapped interpreter — but it does not give the `./pw` verdict stated above.

Until all three hold on a given machine, this document describes the decision
table, not a binding that machine's install provides.

## Registration — orthogonal, on-demand, human-gated

Registration mirrors the existing terminal-title detect→confirm→install model
and is kept ORTHOGONAL to the terminal-title bundle (a project may enable one
without the other).

- **Install surface.** `project install-hook --enforcement` (in
  `claude_runtime.py`, routed through `platform_runtime.py`) adds ONLY the
  matcher-less PreToolUse enforcement entry to `.claude/settings.local.json`,
  without touching the terminal-title render / statusLine / env entries, and
  never duplicates an entry that is already there. It reports
  `enforcement_status` (`installed` / `already_present` / `migrated`).
  `migrated` fires when the entry was already present but carried a stale hook
  `timeout` — a value outside the plausible seconds range, which the re-install
  rewrites to the current one. An entry that is already correct reports
  `already_present` and the file is not written at all.
- **Detect surface.** The `health-check --checks display` diagnostic emits a
  dedicated `PreToolUse:enforcement: present` / `divergence` / `MISSING` label,
  keyed on the enforcement command (not the render command), so a partial,
  absent, or dual-homed enforcement install is diagnosable independently of the
  terminal-title wiring.
  The label is scoped to the **matcher-less** entry: an enforcement command
  parked under some matcher reads `MISSING`, because such an entry does not
  enforce on every tool. The presence probe and the timeout migration carry the
  same scope, so a wrong-matcher entry never suppresses the install of the real
  matcher-less one.
  The enforcement label does not gate the terminal-title `healthy` flag. The
  check inspects BOTH `.claude/settings.json` and `.claude/settings.local.json`:
  an entry in **either file alone** counts as `present`, and an entry in **both**
  reads `divergence`. It matches the `hook` check on both points — the fact that
  a hook entry can legitimately live in either file, and the fact that an entry
  living in both is reported rather than collapsed into `present`. `divergence`
  is report-only: it is an installed entry, so it never makes the check
  unhealthy and nothing repairs or rewrites it. See
  [`contract.md`](contract.md) § `health-check` for the value domain.
- **Menu surface.** The marshall-steward Configuration → Enforcement Hook action
  drives the detect→confirm→install flow; see (**Claude only**)
  [`../../marshall-steward-claude-wizards/references/menu-enforcement-hook.md`](../../marshall-steward-claude-wizards/references/menu-enforcement-hook.md).
- **Human-gated activation.** Writing the live `.claude/settings.local.json`
  entry hits the harness permission prompt and has session-reload activation
  latency, so it is performed by the operator (via the marshall-steward menu),
  not by an unattended task. After registration and a session reload the harness
  arms the hook.
