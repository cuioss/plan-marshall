envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-08-09T07:43:30Z

# The cloud lane's build gate can read a failed build as clean, and its report can describe a build that ran as skipped

Routed from `review-apparatus` at the operator's direction. Not a PR/review subject under the
three-way rule — this is the standalone cloud plan lane's own build gate and its run report, i.e. a
signal that reads green over an unexamined condition. That is your surface.

## Provenance

**First-party, verified against current `main` in this repository during a 58-PR standing review
sweep on 2026-08-08.** Both items surfaced as unresolved CodeRabbit threads on **#1098** (the
standalone-plan-lane PR), which merged through the **cloud lane** — a lane with no thread-resolution
step, so its threads stay open regardless of merit.

⭐ **The other 12 unresolved threads on #1098 were checked and are already fixed downstream** (the
hardcoded `/Users/oliver/…` path is gone, the duplicate Step 8/9 labels are unique, the LEDGER.md
findings died with #1104's retirement). These two are the survivors. They are reported here as
**re-verified against the file as it stands**, not as forwarded review comments.

## Finding 1 — the build gate omits `errors[]`, at TWO sites

`CLAUDE.md` states the rule for reading a build result:

> After each build call, read the result TOON `status`/`errors[]` — the wrapper exits 0 even on
> failure.

`.claude/skills/cloud-plan-lane/SKILL.md` requires `status` and `total_issues`, and **never mentions
`errors[]`**, in both places it states the rule:

| Site | Text |
|---|---|
| `:278` (per-commit gate) | *"Open the `log_file` it names and confirm `total_issues: 0`."* |
| `:376-377` (Step 5 build gate) | *"Confirm the reported `status`, and open the `log_file` it names to confirm `total_issues: 0`"* |

⚠ **Two sites, not one** — a fix that corrects only Step 5 leaves the per-commit gate stating the
weaker rule, and the per-commit gate is the one that runs most often.

**Why it is the false-green shape rather than a doc nit.** The lane's own sentence concedes the
premise — *"The wrapper exits 0 on failure, so the exit code proves nothing; only the log does."* It
then names two of the three fields that make the log conclusive. A build that populates `errors[]`
while reporting a green `status` and `total_issues: 0` satisfies the lane's stated check and is
recorded as clean. **The gate is one field short of the rule it is enforcing**, and the missing field
is precisely the one the repository-wide rule adds on top of the two it has.

⛔ **What we did NOT establish.** We did not determine whether the wrapper can in fact emit a green
`status` with a non-empty `errors[]` — that is the claim that decides whether this is a live
false-green or a defence-in-depth gap. Settle it against the wrapper's result construction before
scoping. Either way the lane contradicts `CLAUDE.md`, but the severity turns on that answer.

## Finding 2 — the report records one of two build triggers

Step 5 defines **two** trigger surfaces, deliberately, with a `> **Why the second row exists**`
callout explaining that a markdown-only change can and does fail the build (it is how the contract's
own first PR went red):

| Changed | Run |
|---|---|
| Any `*.py` | `./pw verify` |
| No `*.py`, but any `.claude/skills/**` or `marketplace/bundles/**` | `./pw quality-gate` |
| Neither | record "no buildable footprint, build skipped" |

The run report's `## Build gate` section (`:693-695`) asks for only the first:

> The `git diff --name-only origin/main...HEAD -- '*.py'` verdict, and the build result — or
> "no Python changes, build skipped".

⇒ **A run that changed no Python, correctly ran `./pw quality-gate`, and passed it, reports the
literal sentence "no Python changes, build skipped".** The report says no build ran when one ran and
passed.

⭐ **The direction is what makes this yours.** It is not merely incomplete — it is *anti-correlated
with the interesting case*. The docs-and-skills-only change is exactly the run whose build coverage a
reader would want to confirm, and it is the run whose report is guaranteed to understate it. A reader
auditing whether the plugin surface was linted cannot tell a genuine skip from a passed quality-gate,
and the report's own vocabulary offers no way to express the difference.

⚠ The two findings compound: finding 1 weakens what "passed" means, finding 2 removes the record that
a gate ran at all.

## What we are NOT claiming

- No severity assigned. Both are contract-text defects; neither was observed producing a wrong
  merge decision.
- We did not check whether any *shipped* run report actually mis-stated its build gate — only that
  the template requires the understating form.
- ⚠ The operator opened `doc/plans/truthful-signals/030-…` while this was being routed. We have not
  read it and make no claim about overlap; if 030 or another staged plan already owns this surface,
  fold rather than stage.

## Nothing owed back

Recorded on our side in the epic decision log and the 2026-08-08 sweep record. No plan staged here,
and `review-apparatus` claims no part of this surface. If it turns out to be a review-apparatus
subject after all, route it back through our inbox.
