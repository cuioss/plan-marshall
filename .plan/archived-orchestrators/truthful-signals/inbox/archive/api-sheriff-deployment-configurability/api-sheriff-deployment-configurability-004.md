envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-11T13:53:46Z

component=plan-marshall:manage-references
category=anti-pattern

# Deltas against a moving or remembered anchor: footprint base is still the bare local `main`, and no rule requires a reviewer's commit range to be derived with `git log A..B`

⛔ **RELOCATED FROM THE WRONG STORE — a MOVE, not a new report.** Two lessons filed in **API-Sheriff's**
store, whose repo does not own the `plan-marshall` bundle. Written here first and removed there second
(integrate-then-remove), `deployment-configurability` epic lessons intake 2026-09-11. The footprint half
is **already forwarded to `code-intelligence-substrate`** — do not re-stage it here.

Origin ids: `2026-08-29-16-004` (created 2026-08-29), `2026-09-02-13-003` (created 2026-09-02).

## Verification at plan-marshall `origin/main` 356973d80 (read-only pass, 2026-09-11)

| Claim | Verdict | Evidence | Already tracked |
|---|---|---|---|
| `compute-footprint` derived against a stale LOCAL `main` reported 183 files for a 4-file change | STILL-VALID | `_references_core.py:157-176` falls back to bare `'main'`, consumed at `_cmd_compute_footprint.py:69`; nothing consults the remote-tracking ref or reports staleness | `truthful-signals-043`/`-045` consumed by `code-intelligence-substrate`, folded into PLAN-CIS-050 D7 (staged, not shipped); related lesson `2026-09-03-05-002` (self-review `--base-branch` against local main) |
| a reviewer was twice handed a hand-written "commits since your last verdict" list containing ancestors of the anchor; ranges must be computed with `git log {anchor}..{head}` at dispatch | STILL-VALID, **UNTRACKED** | no such rule; `agent-behavior-rules.md:264` uses `git log` only to decide whether a branch touched a failing test | none found |

**What this message adds:** a second-repo data point (183 vs 4) for PLAN-CIS-050 D7 — forward as a
sighting; and the commit-range rule in full. Suggested remedy for the latter: any delta handed to a
dispatched agent as context (commit range, files changed since review, findings outstanding since a
triage pass) is computed from the authoritative store at the moment of dispatch and pasted as computed
output, never summarised from session memory or carried forward from an earlier message.

---

## Original lesson `2026-08-29-16-004` (verbatim)

id=2026-08-29-16-004
component=git-workflow
category=anti-pattern
status=active
created=2026-08-29

# Derive a commit delta with git log A..B; never hand-write it from memory

Twice in a single run, a reviewing agent was handed a **hand-written list of "commits since
your last verdict"** assembled from recollection of the session rather than derived from the
repository. Both lists were wrong in the same direction: they contained commits that were
already **ancestors of the review anchor** — work the reviewer had, in fact, already seen.

Both times the reviewing agent detected the error itself, derived the real range from the
repository, and corrected the briefing. That the failure was caught twice by the recipient
is not reassurance: it means the briefing was wrong twice, and it was caught only because
the recipient happened to re-derive something it had been handed as fact.

## The rule

**A commit range is a computed fact, not a remembered one.** Derive it:

```
git -C {tree} log --oneline {anchor}..{head}
```

The `A..B` form is the whole point — it excludes everything reachable from `A`, which is
exactly the "already seen" set that recollection cannot reliably reconstruct. Recollection
fails here in a specific and predictable way: a session remembers *that a commit happened*
but not *where it sits relative to an anchor*, and rebases, squash-merges and merge-queue
rewrites move the anchor underneath the memory.

## Scope

This generalizes past commit ranges to any **delta handed to another agent as context**:
files changed since a review, findings outstanding since a triage pass, tasks remaining in a
phase. If the recipient's work depends on the delta being correct, compute the delta from
the authoritative store (git, the findings ledger, the status file) at the moment of
dispatch, and paste the computed output. Do not summarize it from memory, and do not carry
it forward from an earlier message in the session — the earlier message was true at an
anchor that has since moved.

## Cost when violated

A reviewer given an over-broad range either re-reviews work it already approved (wasted
budget, and a real risk of contradicting its own earlier verdict) or, if it trusts the
briefing rather than checking, reasons about a tree state that never existed.

---

## Original lesson `2026-09-02-13-003` (verbatim)

id=2026-09-02-13-003
component=git-workflow
category=anti-pattern
status=active
created=2026-09-02

# A stale local main ref silently inflates every derived footprint - ff-only sync before trusting one

A footprint derived against a stale local `main` is silently and massively wrong. It does
not fail, warn, or look suspicious — it just reports the union of your change and every
upstream commit you have not pulled, as though you had authored all of it.

## What happened

During finalize for plan `macos-loopback-hang-investigation`, `compute-footprint` reported
**183 changed files** for a branch that actually touched **4**. The extra 179 were upstream
commits already merged to `origin/main` that the local `main` ref had not caught up to
(`#242`, `#244`, `#245` had landed between branch creation and finalize).

Two separate finalize agents each independently hit this, each independently detected the
implausibility, and each worked around it. The remedy was one command on the main checkout:

```
git merge --ff-only origin/main
```

after which the footprint reported 4 files.

## Why it is dangerous

The failure is **silent and directional**. A stale ref never under-reports; it always
over-reports, and it over-reports with entirely legitimate-looking file paths belonging to
real commits. There is no error, no divergence warning, and nothing about the output that
distinguishes "your branch is large" from "your ref is behind."

Everything downstream of a footprint inherits the error. Footprint size feeds
build-gate decisions, review scoping, and PR-size judgements — a 4-file
documentation-only change presenting as a 183-file change routes to an entirely different
gate class than the one it actually needs.

That both agents caught it is not reassurance, for the same reason `2026-08-29-16-004`
gives: it means the derivation was wrong twice, and was caught only because the magnitude
happened to be implausible enough to notice. A stale ref that is behind by *three* files
rather than 179 produces a wrong footprint that looks completely ordinary and gets used.

## Rule

**A footprint is only as current as the ref it is derived against.** Before deriving or
trusting one, confirm the local base ref is not behind its remote:

```
git -C {tree} fetch origin
git -C {tree} rev-list --count main..origin/main    # must be 0
```

When it is non-zero, fast-forward the main checkout before deriving anything:

```
git -C {tree} merge --ff-only origin/main
```

`--ff-only` is deliberate: it syncs when the sync is trivially safe and refuses (rather than
creating a merge commit on the main checkout) when it is not.

Sanity-check the result independently of the tool: a footprint whose size does not match
your own sense of the change is a stale-ref symptom until proven otherwise. Check the ref
before you go looking for an explanation in the tooling.

## Generalisation

Any value computed as a delta against a moving reference — footprints, commit ranges,
"files changed since review", diff-based gate decisions — is a function of that reference
being current. Refresh the reference at the moment of derivation. A long-running plan is
exactly the case where the reference goes stale underneath a session that has no reason to
suspect it.

## Related

- `2026-08-29-16-004` — derive a commit delta with `git log A..B`, never from memory. Same
  family from the opposite side: that lesson is about deltas computed from *recollection*,
  this one about deltas computed correctly against a *stale anchor*. Both produce a
  confident, wrong delta; both were caught only by the recipient noticing.

## Evidence

Plan `macos-loopback-hang-investigation` (2026-09-02, API-Sheriff), PR #243 (merged as
`5948962`). Footprint reported 183 files against a 4-file change; two finalize agents each
detected and worked around it independently.
