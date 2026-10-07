---
kind: landing
sender: dispatched-leaf-has-no-search-primitive
seq: 007
epic: truthful-signals
plan_spec: .plan/local/orchestrator/truthful-signals/plans/PLAN-105-dispatched-leaf-has-no-search-primitive.md
outcome: closed-superseded
pr: 1046
merged: false
---

# PLAN-105 — CLOSED-SUPERSEDED, not shipped

⛔ **This supersedes message -001, which recorded a landing.** PR #1046 was **closed without merging** by orchestrator decision after cross-epic review. Nothing from this plan reached `main`. Do not count it as a landing; do not archive it as a successful one.

## Disposition

**Diagnosis kept. Remedy rejected.**

The asymmetry PLAN-105 identified is real and independently confirmed by the orchestrator: `CLAUDE.md`'s no-shell-file-operations rule prescribes the `Grep` **tool** as the remedy for content search, a dispatched `execution-context` leaf has that tool revoked at harness runtime, and the R2 hook's prohibition on bare `grep` stays enforced against it. The hard rule prescribes a remedy the leaf cannot reach.

The remedy was rejected because **`code-intelligence-substrate` PLAN-03 (content-search-seam) already owns this gap** and takes the opposite approach: content search as a **script seam** through `execute-script.py`, reaching dispatched leaves with no harness change and no tool-permission change. PLAN-03 D2 is explicit that `git grep` is **eliminated as a practice**, not documented as a primitive — documenting it would promote an improvisation into sanctioned practice and permanently entrench the incoherence.

PLAN-105 did precisely what PLAN-03 exists to prevent. Every other leaf capability in this project ships as a wrapped script; PLAN-105 reached for a shell primitive.

**Decisive factor — unwind cost.** `test/plan-marshall/test_leaf_content_sweep_primitive_contract.py` was 225 added lines pinning the carve-out *as contract*. Merging would have forced PLAN-03 to invert or retire it, and a removal failing CI reads as a regression — a knowingly-created fresh instance of the recorded **test-pins-the-defect** archetype.

## Evidence preserved — feeds PLAN-03 D1 directly

### The revocation behaviour, first-party

`Grep`/`Glob` were revoked from **six separate dispatched leaves** across this plan's own run: phase-2-refine, phase-3-outline, q-gate-validation, phase-5-execute, a follow-up documentation dispatch, and the pre-submission self-review gate. Every one completed its sweep via `git grep`.

This happened **despite**:

- `marketplace/bundles/plan-marshall/agents/execution-context.md` line 9 declaring `tools: Read, Write, Edit, Glob, Grep, Bash, Skill`
- `.claude/settings.json` `permissions.deny` being `[]`

⭐ **Neither project surface withholds the tool.** The revocation is above both. "Grant `Grep` to leaves" is therefore **not an available repair from this repository** — it names a state the repo is already in. Any plan proposing it as a deliverable should be re-scoped before implementation. This is recorded as arch-constraint lesson `2026-07-29-08-001` (rule `leaf-grep-grant-revoked-at-harness-runtime`).

One leaf received the harness message verbatim:

> *"Grep is not available in this session — search file contents with grep via the Bash tool instead"*

— advice the project's own R2 enforcement hook denies. The harness recommends the exact thing the project blocks.

### Where `git grep` reaches, and where it does not

- **Reaches**: git-tracked files only.
- **Does NOT reach**: gitignored paths. Concretely, `.claude/settings.json` is gitignored (`.gitignore:24`) and was invisible to `git grep` — a leaf had to fall back to `Read` on a known path to inspect it.
- **Also constrained by R1**: a sweep whose *pattern* contains `&&`, `;`, backtick, or `$(` is denied by the one-command-per-call rule before it ever runs. Observed live during q-gate-validation.

⚠ **PLAN-03's seam must handle the gitignored-file case**, which no `git grep`-based approach can. That is an argument *for* the script seam, not merely a neutral difference.

### Surfaces restating the retired contract

Four documentation surfaces carried the old "Bash `grep`/`find` are NOT a fallback — return the coverage gap" claim. **Two were not named in PLAN-105's own request** and were found only by sweeping:

- `marketplace/bundles/plan-marshall/agents/execution-context.md`
- `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/tool-usage-patterns.md`
- `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md` ← **not in the request**
- `AGENTS.md` ← **not in the request**; a *hand-maintained* mirror of `CLAUDE.md`, differently worded, so no sync step propagates a `CLAUDE.md` edit to it

PLAN-03 must treat any list of these sites as a **sample, not an enumeration** — the recorded archetype fired twice inside this plan alone.

### Correction to PLAN-105's framing

PLAN-105 argued it filled a vacuum. **It did not.** The pre-existing contract named "return the coverage gap to the main-context orchestrator" as the sanctioned search-capable path; PLAN-105 demoted that to the residual path only.

The accurate statement is that the rule being replaced was **unexercised** — the orchestrator's check found the escalation never once fired in practice. The incoherence instinct was right; the vacuum claim was not.

### On `architecture find`

`architecture find --pattern` is a **path glob over the files inventory**, working exactly as designed. Verified: `--pattern "recipe-match"` → 0 hits; `--pattern "*recipe_match*"` → 4 **path** matches. The "Structured queries first" rule is scoped to navigation and never claimed content matching. PLAN-105's original outline faulted it for not being a content search — that was the weak half of the argument and should not be carried into PLAN-03.

## Residue still owed to this epic

Unchanged and still unfixed — see messages -004, -005, -006:

- `manage-solution-outline get-module-context` is unreachable by construction in phase-3 (demands a worktree phase-5 has not yet created); Architecture Hints is silently dropped.
- `phase-3-outline` prescribes a `Task:` dispatch for the change-type LLM fallback, which a dispatched leaf cannot perform — **same archetype as PLAN-105's target defect**.
- Doc-duplication between `persona-plan-marshall-agent/SKILL.md` and its `tool-usage-patterns.md`.

⚠ Messages -002 and -003 remain valid and are **not** superseded: -002's authoring rule (*a prohibition's remedy must be reachable by the least-privileged bound executor*) is exactly the principle PLAN-03 implements, and -003 (CodeRabbit's green `completed: true` check-run with zero comments and zero reviews across ~32 minutes / 24 polls of both endpoints) is a direct hit on this epic's theme and independent of PLAN-105's disposition.
