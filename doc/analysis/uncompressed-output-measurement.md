# Uncompressed command output reaching agent context — decision

Measure-first investigation: does uncompressed command output reaching agent
context justify two follow-up builds? This document is the **decision** the
investigation reached and the **durable, mechanism-level rationale** behind it.

> The original investigation rested on a point-in-time measurement snapshot —
> per-window token totals, transcript counts, and named plans with billed
> figures. Those absolutes were a `char/4` estimate over one analysis window and
> are not figures this project stands behind as a durable record, so they are
> not reproduced here. The decision below rests on the **structural** facts of
> the routing architecture, which are stable, not on those absolutes. To
> re-measure, re-run the analysis against a current transcript window.

The two workstreams the investigation weighed:

- **Workstream A** — a token-waste telemetry lens: quantify tokens entering
  agent context via *raw* Bash output (commands NOT routed through
  `execute-script.py`/TOON), and decide whether a "noisiest uncompressed
  commands" lens is warranted.
- **Workstream B** — a git-output compaction step inside
  `workflow-integration-git` scripts, targeting direct raw `git
  status`/`diff`/`log` output.

## Decision

**Both workstreams: SKIP.** Neither build is justified.

## Rationale (structural, not snapshot)

The decision rests on three properties of the routing architecture, each stable
across analysis windows:

- **The largest output class is already routed.** Test/build runner output —
  historically the single largest output producer — is fully TOON-compressed
  through the `build-pyproject`/`build-maven`/`build-npm` executor wrappers, so
  it reaches context already compact. The compaction Workstream A would add is,
  for the biggest output class, already shipped.
- **The dominant raw-Bash sub-sink is already rule-governed.** The largest
  remaining share of raw Bash output is agent-initiated content search / file
  inspection run through the shell (`grep`/`find`/`ls`/`cat`-family) — precisely
  the pattern the existing `CLAUDE.md` **No shell file operations** hard rule
  already prohibits, and for which the sanctioned answer is `architecture search
  --content --pattern P` (one row per matching file plus a `match_count`, no line
  bodies). Enforcing an existing rule is higher-leverage and adds no standing
  machinery; a surveillance lens over a sink whose dominant component is already
  rule-governed is disproportionate. Note the payload asymmetry that motivates
  the sanctioned route: a raw shell search returns matching line bodies, so its
  size scales with match density, whereas `architecture search --content`
  returns one row per matching file, so its size scales with file count.
- **Workstream B's lever misses its sink.** Git that runs *inside*
  `workflow-integration-git` scripts executes in a Python subprocess whose stdout
  the script consumes; it never surfaces as a Bash `tool_result` and so never
  reaches context. A "compaction step inside `workflow-integration-git` scripts"
  would therefore compress output that is already invisible to context. The
  actual raw `git status`/`diff`/`log` that does reach context is
  *agent-issued* Bash — a small share, with `git status --porcelain` (the bulk)
  already terse — and compacting it would require routing direct git through a
  new executor verb, a far larger change than the return justifies.

## What "routed vs raw" means

The measurement distinguished two output classes, and the distinction is the
durable part of the methodology:

- **Routed** — a Bash command whose text contains `execute-script.py`; its output
  is the compact TOON the executor emits.
- **Raw** — every other Bash command; its stdout/stderr reaches context
  uncompressed. Only raw output is waste under study.

Two structural exclusions follow from the architecture and hold regardless of
window: test/build runner output is routed (never raw), and git executed inside
`manage-*`/`build-*` scripts runs in a subprocess whose stdout never becomes a
`tool_result` — so it is structurally outside the measured surface.

## Higher-leverage observation (no build proposed)

The single most effective reduction in raw-Bash context output is **enforcing
the existing "No shell file operations" rule** — `architecture find` /
`architecture search --content` and the `Glob`/`Grep`/`Read` tools instead of a
shell search program via Bash. That is a compliance/enforcement matter, not a new
telemetry or compaction surface, and is recorded here only as the evidence-based
pointer to where the real waste lives.
