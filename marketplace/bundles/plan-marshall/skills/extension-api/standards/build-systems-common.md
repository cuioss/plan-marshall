# Build Systems — Common Standards

Standards shared across all build systems (Maven, Gradle, npm, Python). Tool-specific details are in each build skill's standards directory.

---

## Timeout Management

See [build-execution.md](build-execution.md) § R3 for the complete timeout learning algorithm and Python API.

**Quick reference**: Default 300s, minimum 60s (the tool-agnostic default floor — overridable per tool), maximum 1800s, discovery 120s. All timeouts in seconds. Adaptive learning uses `last_duration × 1.25` with weighted averaging.

A tool that runs its own inner timeout backstop overrides the default floor via `ExecuteConfig.min_timeout` (threaded into `execute_direct_base`), and MUST set it strictly greater than that inner backstop — otherwise the outer timeout can fire first and reduce a diagnosable inner timeout report to an opaque outer kill.

Every declared floor is ALSO bounded above: `min_timeout + OUTER_TIMEOUT_BUFFER` MUST stay at or below `HARNESS_BASH_CEILING_SECONDS`. The same arithmetic produces the `bash_timeout_seconds` an agent is instructed to pass on its Bash call, so a floor above that bound yields an instruction the host platform cannot honour. Both halves are required when choosing a floor — stating only the lower bound is what permits an over-provisioned floor to ship unnoticed.

---

## Log File Handling

### Log File Pattern

```text
.plan/local/plans/{plan_id}/build-results/{scope}/{tool}-{YYYY-MM-DD-HHmmss}.log
```

- `{plan_id}`: The plan that caused the build, or the `NO_PLAN` sentinel for a plan-less build
- `{scope}`: Module name or `default` for root builds
- `{tool}`: Build system name (maven, gradle, npm, python)

The path is resolved solely by `file_ops.get_build_results_dir(plan_id)` — no other module derives it. See [`build-execution.md`](build-execution.md#r1-log-file-output) § R1: Log File Output for the plan-scoping contract and the sentinel's main-checkout anchoring.

### Output Capture

All output goes to log file. Capture strategy varies per build system:

| Build System | Strategy |
|-------------|----------|
| Maven | `-l` log flag (native) |
| Gradle | stdout redirect + `--console=plain` |
| npm | stdout redirect |
| Python | stdout redirect |

---

## Build Status Determination

### General Rules

| Condition | Status |
|-----------|--------|
| Exit code 0 + success markers | SUCCESS |
| Non-zero exit code | FAILURE |
| Exit code 124 | FAILURE (timeout) |

**Never assume success from exit code alone.** Always verify with log content markers.

### Build System Markers

| Build System | Success Marker | Failure Marker |
|-------------|----------------|----------------|
| Maven | `BUILD SUCCESS` | `BUILD FAILURE` |
| Gradle | `BUILD SUCCESSFUL` | `BUILD FAILED` |
| npm | Exit code 0 | Exit code != 0 |
| Python | Exit code 0 | Exit code != 0 |

---

## Background build execution — reading a long build's completion signal

A build dispatched into the background because it runs long confronts the caller with a question the
obvious signal cannot answer: **is it still running, or was it killed?** The three rules below are
**run-observations** — established by watching a long `./pw` build under the harness, not derived from
a shipped diff. They hold for every build engine, because they are properties of how the executor
emits output and how the harness backgrounds a job, not of any one wrapper.

### The backgrounded job's captured output carries no running-vs-killed information

When a long build dispatch is put in the background, the harness captures the **executor's own
stdout** — and the executor emits its structured result **once, at completion**. So that captured
output is **empty while the build runs**, and **also empty** after the job is killed, because the
executor never reached the emit. **The two states are byte-identical:** an empty captured-output file
is not evidence of "still running" and not evidence of "killed"; it carries no information at all, and
polling it is reasoning from a constant.

Read "output" here as the *backgrounded job's captured stdout* — **not** the build's own streamed log
file under `build-results/…` (see [Log File Handling](#log-file-handling)). That log may fill as the
build runs, but it is not what a background poller is watching, and it is not a liveness oracle either
— a half-written log is as consistent with a killed build as with a running one. Do **not** infer a
background build's liveness from either file; use the change-ledger row below.

### The `kind=build` change-ledger row is the substitute oracle — read `status`, never mere presence

A build that ran to completion appends a `kind=build` row to the change-ledger, stamped with the
`worktree_sha` of the tree it built. This row — not the output file — is the oracle for *"did a build
complete against this working-tree state?"* (see [`../../manage-change-ledger/SKILL.md`](../../manage-change-ledger/SKILL.md)
§ Entry Shapes).

- **A missing row means no build completed** — treat it as fail-closed evidence the tree was **not**
  built, never as "cannot tell." A missing row does not on its own say *why*: a build still in flight
  has no row yet either (the row is written only at completion), so "missing row + zero output bytes"
  is consistent with **both** a running build and a killed one — the same byte-identical ambiguity the
  captured-output rule above describes. It becomes the **whole-tree-kill signature** only once the job
  is known to have **terminated** (the harness reports it no longer running): a terminated job that
  left no row died *before* the dispatch boundary could stamp one, so the missing row plus the 0-byte
  output is then the kill evidence. This is exactly how the `classify-outcome` verb reads it — it takes
  the job's terminated status as an input *alongside* the row/byte check (see
  [`../../manage-change-ledger/SKILL.md`](../../manage-change-ledger/SKILL.md) § classify-outcome),
  never from the row and bytes alone.
- **A present row is NOT unconditionally authoritative — read its `status`.** The row is stamped only
  for a genuine build-executing dispatch: the stamp predicate is a conjunction — a `build-*` notation
  **AND** the build-executing `run` verb **AND** no `--help` anywhere in argv — so a query subcommand
  (`parse`, `discover`, …), a bare `--help`, and a `run --help` probe each write **no** row. But a
  present row proves only that a build-executing dispatch reached the boundary, **not that the build
  passed**: only `status == success` is a pass. `status ∈ {error, timeout, killed, unknown}` each fail
  the freshness gate closed, and `unknown` (exit 0 with no wrapper-claimable status on the payload)
  records an outcome the boundary could not determine — never read it as a green.

> **Enforcement.** The three-way stamp conjunction is enforced at the executor dispatch boundary in
> `tools-script-executor/templates/execute-script.py.template` (`_is_build_class_notation` ANDed with
> the `_mentions_help` conjunct) and pinned by
> `test/plan-marshall/tools-script-executor/test_build_class_stamp_discriminator.py`. A present row
> therefore corresponds to a genuine build-executing dispatch — so read its `status` for the verdict
> rather than trusting mere presence, and treat only `status == success` as a pass.

### The three non-green conditions, and every gate that must keep them apart

A build that does not finish produces **three distinguishable conditions**, and each degrades a gate
in a different direction, so none may be presented as another:

| Condition | Meaning | What it is NOT |
|---|---|---|
| `error` | The build **ran to completion** and reported a failure. | Not a non-finish — a verdict exists. |
| `timeout` | The build exceeded a bound **this stack set**, so this stack sent the kill. | Not a failure; no verdict was reported. |
| `killed` | The build's child died by a signal **nobody in this stack sent**. | Not a failure, and **not a timeout** — no bound fired. |

An outcome that cannot be resolved to one of those is `unknown`, and `unknown` is folded into
**neither neighbour**: it records that the boundary could not read a verdict, which supports no
conclusion in either direction.

**Four outcome surfaces carry these conditions, and the consuming gates read them.** The table is
the derived consumer set — every reader of each surface, enumerated from that surface's closed import
set (`read_entries` + a build-kind filter in any of its three spellings for the ledger — the command
that derives those members is stated below the table — `read_log_verdict` /
`WRAPPER_CLAIMABLE_BUILD_STATUSES` for the wrapper TOON, `job_status` for the daemon wire, and every
reference to `pre-commit-verify-freshness` for the freshness verdict). It is the list a change to the
vocabulary must walk:

| Consuming gate | Surface it reads |
|---|---|
| `_derive_build_status` (executor dispatch boundary) | wrapper TOON `status` + the dispatched script's returncode |
| `_marshalld_supervisor.run_job` (daemon) | job-log TOON via `read_log_verdict` |
| `_build_execute_factory._daemon_result_to_direct` | daemon `job_status` + job-log TOON |
| `_build_shared.cmd_run_common` (emit choke point) | `DirectCommandResult.status` |
| `build_server.py::_render_job_status` | daemon `job_status` |
| `manage-change-ledger classify-outcome` | ledger `kind=build` `status` |
| `manage-tasks pre-commit-verify-freshness` | ledger `kind=build` `status` + `notation` |
| `plan-retrospective analyze-logs.py::summarize_build_ledger` | ledger `kind=build` `status` + `duration_seconds` |
| The agent reading the emitted build TOON | wrapper TOON `status` / `errors[]` |
| `plan-marshall/workflow/execution.md` § Orchestrator-tier phase-5 verification | the orchestrator-tier build's `status` |
| `phase-5-execute/SKILL.md` Step 12a | the freshness verdict's `status` + `reason` |
| `phase-6-finalize/standards/push.md` § Freshness precondition | the freshness verdict's `status` + `reason` |

**The last three are second-order and are the ones a derivation most easily misses.** They do not
read a build status at all — two read the *freshness verdict* that a build status feeds, and one
reads a build outcome the orchestrator (not a leaf) obtained. A consumer set derived only from
"who reads a build `status`" omits all three, yet they are precisely the gates that *degrade*: they
halt a phase transition, halt a push, and decide whether findings get triaged. **Derive the set
transitively — a gate that consumes a verdict derived from the outcome is a consumer of the
outcome.**

#### Re-derive the ledger-reading rows — do not trust the row count

The rows that read the ledger surface directly are derivable by mechanical search, so **run the
derivation rather than trusting this table's length.** Take the intersection of these two sweeps and
drop `_ledger_core.py`, which is the definer of both symbols rather than a consumer of them:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture search --content --pattern "\bread_entries\b" --category script
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture search --content --pattern "kind.{0,14}[!=]=\s*.build\b|\bKIND_BUILD\b" --category script
```

⛔ **The second pattern must cover all three spellings of the build-kind filter** — `== 'build'`,
`!= 'build'` paired with a `continue`, and the `KIND_BUILD` constant. A pattern written for the `==`
form alone under-reports: run against this tree it returns a single file that is not even an importer,
so the intersection is EMPTY and all three ledger-reading members go missing behind a clean-looking
`count` — the `==` spelling is used by no ledger-reading member at all. That is the
defect class this whole section names — a sweep that returns a number is not thereby a measurement.

Read the sweep's `truncated`, `unreadable[]` and `elided[]` fields before believing either result.
`search --content` is inventory-scoped, so a zero is a trustworthy *"not in any inventoried file"* and
never *"not in the tree"* — see
[`../../manage-architecture/standards/client-api.md`](../../manage-architecture/standards/client-api.md) § search.

⚠ **The derived set is a completeness FLOOR for the ledger-reading rows, never a replacement for the
table.** The table is a deliberate superset: it also carries the wrapper-TOON, daemon-wire and
freshness-verdict readers, plus the three second-order gates named above — none of which import the
ledger, and none of which any ledger-anchored sweep can return. A row leaves this table only when the
surface it reads is gone, never because a derivation did not produce it.

**A gate that reads the status field is not thereby discriminating.** Every gate above reads one, so
a list of "gates that read `status`" identifies nothing on its own — the question is whether reading
it changes what the gate DOES. Three failure shapes are what to look for, and all three have occurred
here:

1. **Reads the status, then reports a cause it did not establish.** The freshness gate once described
   every refusal as a worktree mutation, including refusals caused by a kill.
2. **Computes the distinction into a field the next layer rebuilds its payload without.** The
   daemon's `killed` verdict once survived as `error='killed'` and was dropped at the renderer — and
   later, the freshness gate's new `reason` reached neither of its two documented consumers.
3. **Splits an N-way outcome two ways.** A green/red branch has no arm for a non-finish, so whichever
   arm is the `else` silently absorbs it. The orchestrator-tier handler above did exactly this.

**A discriminator that is read and then not acted on is worth less than an absent one, because it
makes the gate look discriminating.**

### Run a long build in the foreground with an explicit 600000 ms Bash timeout — let the harness auto-background

The mitigation that reliably preserved a long build: invoke it in the **foreground** with an explicit
Bash timeout of **600000 ms** (the harness Bash ceiling — see [Timeout Management](#timeout-management)
and [`../../build-pyproject/standards/pyproject-impl.md`](../../build-pyproject/standards/pyproject-impl.md)
§ "Timeout bound ordering") and let the harness auto-background the job at its own ceiling. The
observed asymmetry is the point: **harness-initiated auto-backgrounding preserved the job every time;
caller-initiated background execution was killed twice on the same long build**, producing zero output
and no ledger row. Do **not** background a long build yourself — run it in the foreground at the
600000 ms bound and let the harness manage it.

---

## Acceptable Warnings

### Configuration

Acceptable warning patterns are stored in `run-configuration.json` under the build-system-specific section:

```json
{
    "<build_system>": {
        "acceptable_warnings": [
            "substring pattern",
            "^regex pattern$"
        ]
    }
}
```

Patterns support:
- **Substring matching**: Pattern checked as case-insensitive substring of message
- **Regex matching**: Patterns starting with `^` treated as regex

### Access

```text
Skill: plan-marshall:manage-run-config
Workflow: Read Configuration
Field: <build_system>.acceptable_warnings
```

### Warning Categories

**Infrastructure Warnings (Can Be Acceptable)**:
1. Transitive dependency conflicts
2. Plugin compatibility warnings for locked configurations
3. Platform-specific warnings (OS, runtime version, hardware)

**Fixable Warnings (NEVER Acceptable)**:
1. JavaDoc/documentation warnings — ALWAYS FIX
2. Compilation warnings — ALWAYS FIX
3. Deprecation warnings — ALWAYS FIX (unless external dependency)
4. Code quality warnings — ALWAYS FIX

---

## Canonical Commands

See [canonical-commands.md](canonical-commands.md) for the complete canonical command specification and resolution logic.

---

## Script API

See [build-api-reference.md](build-api-reference.md) for the complete subcommand documentation including parameters, output formats, and tool-specific variations.

---

## Issue Routing

See [build-api-reference.md](build-api-reference.md) § Error Categories for the complete category list per build system and skill routing table.

---

## CI/CD Standards

All build systems support CI mode via environment variables:

| Build System | CI Environment Variables | Additional Flags |
|-------------|--------------------------|------------------|
| Maven | `CI=true`, `MAVEN_OPTS="-Xmx2g -XX:MaxMetaspaceSize=512m"` | `--batch-mode --no-transfer-progress` |
| Gradle | `CI=true`, `GRADLE_OPTS="-Xmx2g -XX:MaxMetaspaceSize=512m"` | `--no-daemon --console=plain` |
| npm | `CI=true`, `NODE_ENV=test` | (non-interactive automatically) |
| Python | `CI=true`, `PYTHONDONTWRITEBYTECODE=1` | Cache `.pyprojectx/` between runs |

See each tool's `*-impl.md` for full CI/CD configuration details.

---

## Common Troubleshooting Patterns

| Issue | Applies To | Solution |
|-------|-----------|----------|
| Memory issues | Maven, Gradle | Adjust `*_OPTS` (`-Xmx2g -XX:MaxMetaspaceSize=512m`) |
| Dependency resolution failures | All | Check descriptor file (pom.xml, build.gradle, package.json, pyproject.toml) |
| Version conflicts | Maven, Gradle | Use `dependency:tree` / `dependencyInsight` |
| Slow builds | Maven, Gradle | Enable parallel builds (`-T 1C` / `--parallel`) |
| Build timeout | All | Increase `--timeout` or check for hanging processes |

See each tool's `*-impl.md` for tool-specific diagnostic commands.
