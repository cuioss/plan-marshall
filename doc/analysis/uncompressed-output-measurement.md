# Uncompressed command output reaching agent context — measurement & decision

Measure-first investigation: does uncompressed command output reaching agent
context justify two follow-up builds? This report is **measurement and decision
only** — no production code, telemetry lens, `workflow-integration-git`, or
`manage-metrics` surface is modified. The single deliverable is this document.

- **Workstream A** — token-waste telemetry lens (RTK discover/gain analog):
  quantify tokens entering agent context via *raw* Bash output (commands NOT
  routed through `execute-script.py`/TOON), bucketed by command family, and
  decide whether a "noisiest uncompressed commands" lens is warranted.
- **Workstream B** — residual git-output gap: isolate *direct* raw
  `git status`/`diff`/`log` output (excluding git run inside Python
  subprocesses, which never reaches context) and decide whether it justifies a
  compaction step inside `workflow-integration-git` scripts.

## Methodology

**Primary data source.** Claude Code session transcripts
(`~/.claude/projects/-Users-oliver-git-plan-marshall/{uuid}.jsonl`). Each line
is one message record. Assistant messages carry `tool_use` blocks
(`name: "Bash"`, `input.command`); the following user message carries the
matching `tool_result` block (`tool_use_id`, `content`). The `tool_result`
content **is** the text that re-enters the model context on the next turn — it
is the authoritative ground truth for "what uncompressed output reached agent
context". Read-only artifacts (per-plan `metrics.md`, the global execution log)
are used only to corroborate magnitude.

**Token estimate.** `tokens = ceil(chars / 4)`. The transcripts carry no
per-`tool_result` token count (the `usage` block is per-assistant-message and
cache-aggregated), so the standard `char/4` fallback is used uniformly. All
absolute figures below inherit this ±~15% estimation band; the **relative**
shares (the basis of every decision) are far more robust than the absolutes.

**Routed vs raw.** A Bash command whose text contains `execute-script.py` is
**routed** — its output is the compact TOON the executor emits. Every other
Bash command is **raw** — its stdout/stderr reaches context uncompressed. Only
raw output counts toward the waste numerator.

**Family buckets (Workstream A).** Each raw command's first executable token
(after stripping any leading `cd … &&`) maps to one of four families:

```toon
families[4]{family,members}:
  git,"git (any subcommand, incl. -C)"
  ls/grep/find,"ls grep find cat head tail wc awk sed rg tree du sort uniq cut"
  test-runners,"pytest mvn npm npx gradle jest tox node ./pw (direct, un-routed)"
  misc,"everything else: gh, test, echo, mkdir, python3 (non-executor), …"
```

**Workstream B exclusion rule.** Workstream B counts only commands matching
`^\s*git\b(\s+-C \S+)?\s+(status|diff|log)\b` that are **raw** (no
`execute-script.py`). Git executed inside `manage-*`/`build-*` scripts runs in a
Python subprocess whose stdout is consumed by the script and never surfaces as a
`tool_result` — those invocations are structurally excluded because they never
appear as a Bash `tool_use` in the transcript.

**Plan attribution.** Each record's `gitBranch` (`feature/{plan_id}` etc.) or
`cwd` (`…/worktrees/{plan_id}/…`) attributes its output to a plan; records on
`main` (orchestrator work, phases 1–4 before worktree materialization, ad-hoc
work) bucket as `@main`.

**Scope.** All 123 transcripts with mtime ≥ 2026-06-14 (the recent ~2-week
window), spanning 122 distinct plan branches. Reproduce via
`.plan/temp/measure_output.py` (the analysis script; not committed as product
code — read-only measurement tooling).

## Workstream A — raw Bash output reaching context

### Context totals (all `tool_result` text reaching context, recent window)

```toon
context_totals:
  total_tool_output_tokens: 11540648
  routed_execscript_tokens: 2590206   # 22.44% — TOON-compressed executor output
  other_tool_tokens: 8315356          # 72.06% — Read/Grep/Glob/Edit tool results
  raw_bash_tokens: 635086             #  5.50% — the waste surface under study
  raw_bash_calls: 3849
```

Raw Bash output is **5.50%** of all tool-output text entering context. The
dominant share of context tool output is the `Read`/`Grep`/`Glob`/`Edit` tool
family (72%), and the executor's own TOON output (22%) is already compact.

### Per-family breakdown (Workstream A core table)

```toon
workstream_a_by_family[4]{family,calls,tokens,share_of_raw,avg_tok_per_call}:
  git,2212,168400,26.5%,76
  ls/grep/find,807,382525,60.2%,474
  test-runners,0,0,0.0%,0
  misc,830,84161,13.3%,101
```

Interpretation:

- **`ls/grep/find` dominates (60.2% of raw, 382K tokens)** at the highest
  per-call cost (avg 474 tok/call). This is agent-initiated content search /
  file inspection run through Bash — precisely the pattern the existing
  `CLAUDE.md` hard rule "**Never use Bash for file operations** … use Glob,
  Read, Grep tools instead" already prohibits. The waste here is a
  *rule-compliance* problem, not a missing-telemetry problem.
- **`test-runners` is exactly 0.** Historically the single largest output
  producer, test/build output is **already fully routed** through the
  `build-pyproject`/`build-maven`/`build-npm` executor wrappers (which emit
  TOON). The compaction this plan asks about is, for the biggest output class,
  *already shipped*.
- **`git` (26.5%, 168K)** is the second family; Workstream B drills into the
  direct-git slice of it below.
- **`misc` (13.3%)** is long-tail (`gh pr checks --watch`, `test -f`, etc.).

### Top noisiest individual raw invocations

```toon
workstream_a_top_noisiest[10]{tokens,family,command_prefix}:
  6732,ls/grep/find,"grep -rn resolve-execute-task-skill… (multi-alternation)"
  6423,ls/grep/find,"grep -n AssertionError|assert|Error over a worktree .plan path"
  5560,ls/grep/find,"awk NR>=621&&NR<=6180 over a transcript jsonl"
  5519,misc,"gh pr checks 348 -R cuioss/nifi-extensions --watch --interval 60"
  5204,ls/grep/find,"grep -rnE .claude|opencode|known_marketplaces… over tree"
  4283,ls/grep/find,"grep -F broken-relative-link over a /tmp findings dump"
  4203,ls/grep/find,"grep -n -i rebase|auto_rebase|stale… over a skill"
  4192,ls/grep/find,"grep -rn Task: execution-context|dispatch over bundles"
  3688,git,"git -C …/qgate-add… show a950d… (full diff)"
  3115,git,"git -C …/persona-ref… status --porcelain --untracked"
```

The noise is concentrated in a **handful of broad multi-alternation greps over
large files** (transcripts, finding dumps, whole-tree scans). The single
noisiest invocation is 6.7K tokens; the top ~10 together are ~50K (≈8% of all
raw Bash). A "noisiest commands" lens would mostly re-surface invocations that
already violate the no-Bash-for-file-ops rule.

### Share of total plan tokens

```toon
workstream_a_share_framing:
  raw_bash_share_of_tool_output: 5.50%
  raw_bash_per_session_avg_tokens: 5163        # 635086 / 123 sessions
  typical_total_billed_plan_tokens: ~2000000   # e.g. align-plan-marshall: 2,047,559 (metrics.md)
  raw_bash_share_of_billed_plan_tokens: ~0.3% – ~0.8%
```

Against **new tool-output text** raw Bash is 5.5%; against **total billed plan
tokens** (cache-read dominated, ~2M/plan per `metrics.md`) it is a fraction of a
percent. Per-plan raw share among the busiest plans peaks at ~20% of *tool
output* (e.g. `qgate-add-call-sites…` 20.6%, `adopt-gate-ci-structure` 20.2%),
but the absolute magnitude is small (6–16K tokens/plan). The `@main` bucket
holds the largest absolute raw total (278K) because it aggregates orchestrator
work, phases 1–4, and all ad-hoc sessions across 2 weeks.

## Workstream B — direct raw `git status`/`diff`/`log`

```toon
workstream_b_totals:
  direct_git_sdl_calls: 818
  direct_git_sdl_tokens: 68868
  avg_tokens_per_call: 84.2
  share_of_raw_bash: 10.84%
  share_of_total_tool_output: 0.597%
```

```toon
workstream_b_by_subcommand[3]{subcommand,calls,tokens,avg_tok,max_tok}:
  status,663,42682,64.4,3115
  diff,59,17006,288.2,2987
  log,96,9180,95.6,423
```

```toon
workstream_b_top_noisiest[6]{tokens,subcommand}:
  3115,status
  2987,diff
  2694,status
  2670,status
  2543,status
  1468,status
```

Interpretation:

- **`git status` is frequent but cheap** — 663 calls (81% of the SDL count) at
  avg 64 tokens each; most are `--porcelain` output that is already terse. The
  freshness/commit flow drives the call count, not the token volume.
- **`git diff` is the costliest per call** (avg 288 tok) but rare (59 calls).
- Direct git status/diff/log is **0.597% of total tool-output tokens** — about
  one part in 170 of context tool output.
- **The proposed lever does not map to the sink.** The 818 calls are
  *agent-issued* raw Bash. Git that runs *inside* `workflow-integration-git`
  scripts already executes in subprocesses and never reaches context, so a
  "compaction step inside `workflow-integration-git` scripts" would compress
  output that is already invisible to context — it would not touch any of the
  measured 68.9K tokens. Compacting the agent-issued slice would instead require
  routing direct git through a new executor verb, which is a larger change than
  the 0.6% sink justifies.

## Decision summary

Each row states the numeric threshold the verdict rests on, the measured value,
and the verdict.

```toon
decision_summary[2]{workstream,threshold,measured,verdict}:
  A (noisiest-commands telemetry lens),"build iff raw Bash ≥ 15% of tool-output tokens (or ≥ ~10% of billed plan tokens) AND not already governed by an existing rule","5.50% of tool output (~0.3–0.8% of billed); 60% of it is ls/grep/find already prohibited by the no-Bash-for-file-ops rule; test-runners already 0 (routed)",SKIP
  B (git-output compaction in workflow-integration-git),"build iff direct git status/diff/log ≥ 5% of tool-output tokens OR avg ≥ 500 tok/call at high frequency, AND the sink is actually produced by workflow-integration-git script stdout","0.597% of tool output; avg 84 tok/call; sink is agent-issued raw git, NOT script stdout (script git runs in subprocesses, never reaches context) — proposed lever misses the sink",SKIP
```

### Rationale

- **A — SKIP.** Raw Bash output is a small, well-bounded share of context
  (5.5% of tool output; sub-1% of billed plan tokens). The largest sub-sink
  (`ls/grep/find`, 60%) is already prohibited by the existing
  no-Bash-for-file-ops hard rule — enforcing that rule is a higher-leverage,
  zero-new-machinery fix than a surveillance lens. The historically largest
  output class (test/build runners) is already fully TOON-routed (measured 0).
  A dedicated telemetry lens folded into `manage-metrics`/the retrospective
  audit would add standing machinery to watch a 5.5% sink whose dominant
  component is already rule-governed — disproportionate.
- **B — SKIP.** Direct git status/diff/log is 0.6% of context tool output at
  avg 84 tok/call; `git status --porcelain` (the bulk) is already terse. The
  proposed compaction lever is aimed at `workflow-integration-git` scripts whose
  git already runs in subprocesses and never reaches context, so it would not
  reduce the measured sink at all; the actual sink is agent-issued raw git,
  which would need a new executor route to compact — far more cost than a 0.6%
  return.

### Higher-leverage observation (no build proposed here)

The single most effective reduction in raw-Bash context output would come from
**enforcing the existing "no Bash for file operations" rule** (Glob/Grep/Read
instead of `grep`/`find`/`awk` via Bash), which alone accounts for ~60% of all
raw Bash output. That is a compliance/enforcement matter, not a new telemetry or
compaction surface, and is explicitly out of scope for this measurement plan —
recorded here only as the evidence-based pointer for where the real waste lives.

## Caveats

- Absolute token figures use the `char/4` estimate (±~15%); decisions rest on
  relative shares, which are robust to that band.
- Scope is the recent 2-week window (123 sessions); long-tail historical
  behavior may differ, but the routing architecture (test runners → executor
  TOON; script git → subprocess) is stable, so the qualitative conclusions hold.
- `tool_result` token volume is the "new text entering context" denominator;
  billed plan tokens (cache-read dominated) are strictly larger, making every
  share above an **upper bound** on the share of total plan tokens.
