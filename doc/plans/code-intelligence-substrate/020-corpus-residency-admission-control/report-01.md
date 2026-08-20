# Run report — 020-corpus-residency-admission-control (run 01)

**Date (UTC):** 2026-08-10 &nbsp;&nbsp; **Branch:** `claude/corpus-residency-admission-control-p6zv1u` (harness-assigned; kept as-is per the lane contract) &nbsp;&nbsp; **PR:** [#1149](https://github.com/cuioss/plan-marshall/pull/1149) &nbsp;&nbsp; **Outcome:** blocked (D0 gate halted on corpus availability — a real, reported outcome, not a failure)

## Summary

The plan opens with **D0 — a GATE**: can the corpus-residency population be derived in this clone at
all? Its done-condition is (a) a git-reachable population of instrumented records to measure, or
(b) that no such population is reachable here — and on (b) the plan directs: **HALT, report the plan
blocked on corpus availability, and stop; do not proceed to D1–D4, and do not substitute a
hand-assembled stand-in.**

This run established, from git-reachable evidence alone, that the answer is **(b)**. The plan is
**blocked on corpus availability**. Per the plan's Verification section, "a run that halts at D0 with
a clear statement of what was unreachable has succeeded at D0" — so D0 itself is satisfied; D1–D4
were correctly not attempted.

## Skills loaded

Loaded by reading the bundle source path (the `plan-marshall` plugin is not assumed present in this
cloud session):

- `cloud-plan-lane` — the working contract, loaded first (via the `Skill:` route, which succeeded here).
- `plan-marshall:ref-code-quality` (always) — read from `marketplace/bundles/.../ref-code-quality/SKILL.md`.
- `pm-plugin-development:plugin-script-architecture` (always) — read from its bundle path.

**Conditional domain skills were deliberately NOT loaded** (`persona-implementer`, `pm-dev-python:python-core`,
`pm-dev-python:pytest-testing`, `pm-plugin-development:plugin-architecture`, `pm-documents:ref-asciidoc`,
`plan-marshall:ref-workflow-architecture`). The run halted at D0 before any implementation surface was
touched, so loading production-code or mechanism skills would have been pure context cost with nothing
to apply them to. The D0 investigation needs only Read/Glob/Grep, which require no skill. None was
unobtainable; they were unneeded.

## Deliverables

| Deliverable | Outcome |
|---|---|
| **D0 — GATE: can the residency population be derived in this clone?** | **HALT (b).** No git-reachable population of instrumented corpus-residency records exists here. Evidence below. Established from git-reachable evidence alone. |
| **D1 — derive the corpus-residency population** | **Not attempted — gated by D0.** D1 measures archived instrumented records; none are reachable (D0). Proceeding would require a hand-assembled stand-in, which the plan forbids. |
| **D2 — section-granular corpus read verb** | **Not attempted — gated by D0.** The plan forbids building D2 on a single observation or an unverified population premise. |
| **D3 — re-read elimination within an envelope** | **Not attempted — gated by D0.** Its magnitude is supplied by D1, which could not run. |
| **D4 — restate the epic's value case against the measurement** | **Not attempted — gated by D0.** There is no measurement to restate the value case against. |

### D0 evidence — why the population is unreachable

The measurement this plan rests on is the per-phase metrics field **`exploration_doc_residency_bytes`**
(with siblings `exploration_index_answerable_bytes` and `exploration_unattributed_bytes`), written by
the `manage-metrics` `enrich` transcript walk. Per its schema
(`marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md`), it is "the part
[of exploration bytes] whose call targeted a workflow/standard document: skill and standard markdown
bodies, `doc/**`, `*.adoc`, `CLAUDE.md`" — exactly D1's "how much of each read document a step
actually consumes."

1. **The records live only under a git-ignored path.** `data-format.md` states plainly: "All files
   live in `.plan/plans/{plan_id}/`." `.gitignore` ignores `.plan/*` and allows back only
   `!.plan/marshal.json` and `!.plan/project-architecture/`. So no `metrics.toon` — the sole carrier
   of the doc-residency measurement — is ever tracked.

2. **The archived population is under a git-ignored path too, and absent.** The archived-plan audit
   (`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`) walks
   `.plan/local/archived-plans/{plan_id}/`. That directory does not exist in this clone.

3. **The clone's `.plan/` contains no records at all.** A full listing shows only `.plan/marshal.json`
   and `.plan/project-architecture/{module}/enriched.json` — the architecture *inventory* (which files
   and modules exist), **not** any per-phase document-read measurement. There is no `.plan/plans/`,
   no `.plan/local/`.

4. **Zero git-tracked `metrics.toon`.** `git ls-files "*metrics.toon"` returns nothing. The only
   git-tracked instrumented `.toon` records are three **synthetic test fixtures** under
   `test/plan-marshall/plan-retrospective/fixtures/dispatch-loop-replay/{legacy,plan,unmeasured}/work/metrics-dispatch-boundaries-5-execute.toon`.
   These (a) are hand-crafted test inputs — the plan explicitly forbids substituting a hand-assembled
   stand-in — and (b) carry per-*dispatch* context-load columns (`input/output/cache` tokens), not the
   per-*phase* `exploration_doc_residency_bytes` measurement D1 needs.

5. **The field appears in git only as schema/producer/test code, never as data.** Every git-tracked
   occurrence of `exploration_doc_residency_bytes` is in a schema doc, the producer source
   (`platform-runtime/scripts/runtime_base.py`, `contract.md`), or test code — no populated record.

6. **This is a deliberate, epic-wide condition, corroborated by a sibling plan.** Plan
   `080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case.md` carries the **identical**
   D0 gate: "is an instrumented population reachable in this clone at all? The records this plan
   measures are archived run artifacts under a machine-local, git-ignored [path]." D0 exists precisely
   to catch this absence; it is not an unexpected error.

**The prohibition was respected.** The originating per-phase measurement (labelled "NOT REACHABLE FROM
THIS CLONE") was not searched for or read; `.plan/plans/` / `.plan/local/` were confirmed structurally
absent via `git ls-files` and a top-level `ls .plan`, which is establishing (b), not mining the
measurement. No hand-assembled stand-in was constructed. n=1 re-derivation from this session's own
transcript was not attempted (the plan forbids building on a single observation, and a live-session
transcript is neither git-reachable nor a population).

## Build gate

`git diff --name-only origin/main...HEAD` touches only `doc/plans/**` (the plan-directory move and
this report) — **no `*.py`**. Per the lane contract the local build gate is keyed on `*.py`, so:
**no buildable footprint, build skipped.** The merge queue's `merge_group` run verifies the docs-only
change before it lands.

## Findings

### Pre-PR verification sub-agent (Step 6) — dispatched adversarially

An independent, read-only sub-agent (`general-purpose`) was dispatched to **refute** the D0 halt: to
find any git-reachable population of instrumented corpus-residency records D1 could measure. It reports,
it does not fix.

**Verdict: HALT-CONFIRMED.** It independently re-verified all four evidence claims and ran further
adversarial searches, and could not refute the halt. Its confirmations and additional searches:

- **All four evidence claims independently verified** — the `exploration_doc_residency_bytes` per-phase
  definition (`data-format.md:152`); the "All files live in `.plan/plans/{plan_id}/`" storage line
  (`data-format.md:13`) against the `.gitignore` un-ignore set; zero git-tracked `metrics.toon`; and the
  field appearing in exactly five tracked files, all non-data (two tests, two schema/contract docs, one
  producer).
- **Committed run reports** (`doc/plans/**/report-*.md`) grepped for residency/consumption vocabulary —
  **no matches**; the one sibling report (010-lsp) is entirely LSP-latency and carries no residency data.
- **A committed transcript corpus** a D1-style `enrich` walk could itself consume — **none tracked**
  (`*.jsonl`/session JSON); transcripts live in git-ignored `~/.claude`, so there is not even raw
  material to re-derive from.
- **`.plan/project-architecture/*/enriched.json`** (the only other tracked `.plan/` content) — is
  architecture inventory, **no** metrics fields.

**Findings raised by the sub-agent (both consistent with the halt, neither a defect):**

1. **A fourth synthetic fixture, not named in the run's original evidence** —
   `test/plan-marshall/plan-retrospective/fixtures/archived-plan/work/fragment-plan-efficiency.toon`.
   *Disposition: no change.* It has a per-phase `duration_seconds`/`tokens` breakdown but **no residency
   field**, and is plainly synthetic (`plan_id: lesson-2026-04-18-13-001`, under `fixtures/`). A
   hand-crafted fixture is exactly the substitution the plan forbids — its existence supports, not
   refutes, the halt. (Strengthens the report; changes nothing.)
2. **A false-positive on the word "residency"** — `manage-config/standards/domain-residency-audit.md`
   concerns **config-domain** residency (which domain's content resides in the core bundle, per ADR-010),
   an unrelated sense of the word. *Disposition: correctly excluded.* Not corpus/document residency.

The sub-agent's one stated caveat is the intended D0 condition itself: the originating measurement
genuinely lives under git-ignored `.plan/plans/`, absent here, confirmed structurally without mining it.
It also noted the absence is **total** — even the parent field `exploration_result_bytes` has no
populated git-tracked record, so there is not even partial data to re-slice.

**Disposition of the run's D0 conclusion:** accepted, independently verified. No defect found in the
halt; the sub-agent's two findings both reinforce it.

### CI

Read from actual check state (`pull_request_read get_check_runs`) on PR #1149. The diff is docs-only,
so `python-verify.yml`'s `skip-on-docs-only` path fires:

- **`verify / conclusion` = success** (the required check) — with `verify / verify` = **skipped**
  (the heavy build skipped for a docs-only footprint) and `verify / gate` = **success**.
- `Sourcery review` = skipped; `auto-merge` = skipped. `review / review` and `dependency-review` are
  **non-required** (`mergeStateStatus`/`mergeable_state: unstable` confirms every *required* context
  passed and only non-required ones remained pending).

No CI failure. The final pre-merge report commit re-triggers `verify` on the new head; the required
`verify / conclusion` was re-confirmed green on that head before auto-merge was armed.

## Reviewer participation

Expected population derived from the automatic-review registry `author_login` fields
(`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{coderabbit,pr-agent,sourcery}.md`;
cross-named in `.github/workflows/pr-agent.yml`). This is a genuine **no-reviewable-footprint** diff —
`doc/plans/**` only, no `*.py`, no `.claude/skills/**`, no `marketplace/bundles/**` — so `skip-bot-review`
was applied at PR creation. Verdicts read from the stored comment **bodies** (not from the label, a
check state, or an assumption):

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted a "PR Reviewer Guide" over the diff: *"No relevant tests · No security concerns identified · No major issues detected."* A clean, no-findings review. Its Guide comment is **unconditional** — the pr-agent registry records that `skip-bot-review` gates only its inline `/improve` comments, not the Guide — so it reviewed despite the label. Nothing to disposition (clean). |
| `coderabbitai` | `silent` (by design) | Posted only a skip-acknowledgement notice, not a review: *"Review skipped — only excluded labels are configured … skip-bot-review."* `honors_skip_label: true`. No review of the diff. |
| `sourcery-ai` | `silent` (by design) | Posted nothing; its `Sourcery review` check concluded **skipped**. No review of the diff. |

**Coverage: 1 of 3 reviewed.** `cuioss-review-bot` reviewed and found no issues; `coderabbitai` and
`sourcery-ai` were intentionally suppressed by `skip-bot-review` (correct for a diff with no reviewable
footprint). The § Step 8 shortfall disclosure fired and is stated to the operator as: *"Review coverage
1 of 3 — `cuioss-review-bot` reviewed (clean: no relevant tests, no security concerns, no major issues);
`coderabbitai` and `sourcery-ai` suppressed by the `skip-bot-review` label, which is by design for a
doc-only diff."* Per the contract this is a **disclosure, not a block**: the suppression is by design for
this diff class, not a rate-limit or an outage, so the merge is not held on it.

(The `cla-assistant` bot separately reported CLA status `not_signed` for the human account — an
operator/account concern, not a code-review finding, and not among the repo's required merge checks.
Disclosed, non-blocking; the CLA is managed on the operator's side.)

## Cost

- **Tokens:** not available to the agent in this session — this interactive Claude Code cloud session
  does not surface its own token accounting, so no figure is stated rather than a guessed one.
- **Wall-clock:** a single short interactive cloud session (recon → D0 determination → report → PR).
- **Population:** whatever the above would count is this one interactive cloud session. It is **not
  comparable** to a plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent
  dispatch tree under plan-marshall's per-task billing boundary — a boundary this session does not
  share. Reported without a comparison.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — `cloud-plan-lane` (first), `ref-code-quality`, `plugin-script-architecture`. Conditional domain/production-code skills deliberately **not** loaded: the run halted at D0 before any implementation, so they had nothing to apply to. **GitHub access path: GitHub MCP server** (cloud path). **Branch form: harness-assigned** `claude/*`, kept as-is. |
| 2 Branch on origin | Done — the harness-assigned branch was **absent from the remote** on arrival; pushed as the first action, and after every commit. |
| 3 Plan directory | Done — `…/020-corpus-residency-admission-control/plan.md` exists and opens with the first-instruction block (present in the source; preserved by the `git mv`). |
| 4 Implement | Done to the extent the plan permits — D0 gate executed → **HALT (b)**; D1–D4 correctly not attempted (each gated by D0, and the plan forbids proceeding on a stand-in / n=1). Commits carry the `Co-Authored-By: Claude` trailer. |
| 4 Per-commit gate | **N/A** — no commit touched `*.py`, so the `*.py`-keyed quality gate had no trigger. |
| 4 Pushed | Done — no unpushed commit remains (this report is the final pre-merge commit). |
| 5 Build gate | Done — git-derived verdict: **no `*.py` in `origin/main...HEAD`** → "no buildable footprint, build skipped." The merge queue's `merge_group` run verifies the docs-only change. |
| 6 Verification sub-agent | Done — dispatched adversarially (read-only, `general-purpose`); **HALT-CONFIRMED**; two findings, both reinforcing the halt; dispositions recorded (§ Findings). |
| 7 PR cycle | Done — PR #1149; `skip-bot-review` applied at creation (no reviewable footprint); **both** comment surfaces read (inline threads: empty; conversation: CodeRabbit skip-notice + CLA status); every comment dispositioned (§ Reviewer participation). |
| 8 Merge gate | Conditions 1–3 met: required `verify / conclusion` green on the head; every comment handled; this report finalized as the last pre-merge commit **before** arming. Condition-4 shortfall (1-of-3) disclosed (§ Reviewer participation). Auto-merge armed (squash). **`MERGED` not self-confirmable in-session** (no self-wake: `send_later`/`subscribe_pr_activity` approval-gated, Bash cannot poll) → landing **delegated to the orchestrator collect** — a completed arm-and-hand-off, not a partial run. |
| 8 Bridge | No write landed under `doc/plans/` outside this plan's own directory — no ledger, no status file, no other plan touched. The report carries the PR number and per-deliverable outcome the orchestrator collects from. No `/sync-plugin-cache` owed (cloud run; no `marketplace/bundles/**` edit). |
| 9 This check | Appended here. |
| 9 What have we learned | Recorded below. |

## What have we learned (Step 9)

**No contract change proposed.** The `cloud-plan-lane` contract handled a D0-halt run cleanly and
without ambiguity that this run had to resolve against the text:

- The **blocked outcome** has a defined home — Step 8 states *"Your report is the channel back … the
  outcome per deliverable, including a run that ended blocked or partial, and why,"* and the bridge
  (`cloud-bridge.md`) explicitly anticipates a run reporting `blocked` and being collected from its
  report. So a D0 halt is a first-class outcome the contract already carries end to end.
- The **land-the-report path** for a blocked run followed from existing rules: the report is the only
  durable channel (Step 2), the bridge's collect step reads it from a **merged** PR (Path 3), and the
  diff is a no-reviewable-footprint doc change so `skip-bot-review` applies (Step 7). Nothing had to be
  invented.

One **observation, not a proposal** (recorded for transparency, per Step 9's bar that a proposal must
name a concrete in-run failure or ambiguity, which this did not reach): the merge gate (Step 8) is
phrased around a run that *ships deliverables*, and a first-time reader executing a **blocked-at-D0**
run must assemble "still open a PR, still land the report, still arm the merge, and let collect keep the
plan queued rather than shipped" from three separate sections (Step 8, the bridge, Step 7) rather than
one. This run resolved it correctly and was not blocked by it, so it does not meet the threshold for a
proposed edit — but if a future run reports genuine hesitation here, a one-paragraph "a blocked/halted
run still lands its report" note at Step 8 would be the fix. Left to the operator's judgement; no PR
opened for it.

## Residue

- **The plan is blocked on corpus availability, not retired.** It becomes runnable when a git-reachable
  population of instrumented corpus-residency records exists — e.g. executed in a local session where
  `.plan/plans/` / `.plan/local/archived-plans/` are present and populated, or once a sibling
  measurement plan lands a git-reachable population. The orchestrator's collect step should keep 020
  queued (not mark it shipped) and re-hand it when the corpus is reachable.
- **Coordination note carried forward for the eventual D2:** plan 010 (`lsp-in-execute-lookup-and-write`,
  PR #1140) shipped a reusable `lsp-client`. Its closing note explicitly anticipates "a sibling WS-06
  plan [that] wants this same client pointed at the document corpus." When 020 is un-blocked and D2 is
  built, coordinate with that client rather than forking a second one — **and re-verify at outline**
  whether an LSP-shaped client (built for code symbols) is the right shape for section-granular reads
  over markdown documents, or whether `manage-architecture`'s existing content-search surface is the
  better home (the plan's Expected-surface leaves this open).

  > **Correction appended by plan 500 (`500-lsp-and-derivation-resolver-correctness`), covering
  > `020/G12`.** The note above points at the wrong surface, and its question has more candidates than
  > the two it names. This is appended rather than rewritten: the note records what this execution
  > concluded, and that record stands.
  >
  > **The surface to coordinate with first is `pm-plugin-development:tools-corpus-language-server`,
  > not `plan-marshall:lsp-client`.** The note was written when the only shipped LSP surface was a
  > **code-facing client** — one that spawns a third-party language server over source files. A
  > **corpus-facing resident server** has shipped since, over the marketplace document corpus, and it
  > already solves the three problems D2 would otherwise re-solve: the index, the resident cost model
  > (~1.9 s build paid once at `initialize` rather than per call), and the opt-in switch.
  >
  > **It does not satisfy D2, and the limit is granularity.** Its index is **component-granular**:
  > `_corpus_index.py` records no intra-file position, `definition` returns the owning component's
  > file at **line 0** by explicit design, and `hover` returns description plus frontmatter. D2 needs
  > **section-granular** reads — a heading or anchor within a document — and the server has no heading
  > or anchor concept at all. Extending it is a real change, not a call.
  >
  > **The open question is three-way, not two-way.** The note also predates the removal of the LSP
  > query facade (plan 135), so the candidate set it names is stale. Pose it as: extend
  > `tools-corpus-language-server` with a section-granular request; extend `manage-architecture`'s
  > content surface; or extend a `--section` verb on the document surface. `plan-marshall:lsp-client`
  > is not among the candidates — it is a client of a *code* language server and reads no documents.
