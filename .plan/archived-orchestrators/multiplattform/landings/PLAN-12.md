# Landing Analysis: PLAN-12 — cross-bundle assistant prose

epic: multiplattform
workstream: WS-03
pr: #1460 (https://github.com/cuioss/plan-marshall/pull/1460)

> Landing record for one shipped plan. Lives at `landings/PLAN-12.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact.

Drained from `inbox/cross-bundle-assistant-prose-001.md` **at revision 3**, corroborated against
the merged diff (`9c23d54e1`), the CI abstraction, and the worktree state. **This closes WS-03 —
the last non-parked workstream in the epic.**

⚠️ **Provenance note, stated rather than glossed:** this drain ran against the message and the tree,
not against the review cycle that produced its three amendments. The critique that prompted the
operator's four fixes is not in this session's context, so every claim below was re-verified from
ground truth rather than accepted on the strength of "fixed".

## ⭐ The first `complete: true` landing in this epic

`inbox landing-check` → **`complete: true`, `missing_keys: []`**. After **eleven consecutive**
landings reporting `total_tokens=unknown`, this one supplies it: **45,220,283**, and — more
importantly than the number — it supplies the number **with its population named and its exclusions
stated**:

> main session 42,575,467 + pre-PR verification sub-agent 2,299,893 + Step-6 re-check 344,923,
> summed from raw input+output+cache_read at `2026-09-10T12:53:52Z`, `cache_write` untracked.
> The 2026-09-09 session is **PLAN-07** and the 2026-09-08/09 session is **PLAN-06** — neither
> belongs to this plan, and both are excluded.

⭐ **The correction is more instructive than the figure.** An earlier reading attributed three work
sessions to this plan; attribution against the sessions' own first messages refuted it — two of the
three belong to sibling plans that had already landed. This is the same class the epic has been
recording all along: **a count published without its population is not a measurement.** Here the
population is named, the exclusions are justified by evidence, and the figure is explicitly labelled
a live snapshot rather than a sealed total. That is what the standing lane defect has been asking
for since PLAN-04.

## ⭐ The 2026-09-09 narrowing was validated in practice

The narrowing declared `pm-documents/skills/**` and `pm-dev-frontend/**` **sweep-only** — declared so
the plan would look, not edit. The merged diff touches **neither**. The three dispositions held
exactly as recorded:

| Narrowing decision | Outcome |
|---|---|
| `content-review.md` + `ref-svg-diagrams/SKILL.md` already closed by PLAN-05 | Untouched ✅ |
| `pm-dev-frontend` ×3 are an Anthropic-ships **attribution**, rewording would make them false | Untouched ✅ |
| ⛔ `recipe-doc-verify/SKILL.md` already correct — **rewording would regress it** | Untouched ✅ |

⭐ The regression hazard is the one worth noting: it was recorded specifically because a plan
sweeping that glob would plausibly "fix" already-correct per-target prose. It did not, and the
recorded hazard is the reason to believe that was deliberate rather than lucky.

## ⛔ Two undeclared paths — disclosed, but the SPEC's surface still was not updated

Realized **10**, declared **8** entries, **2 undeclared**:

- `script-shared/scripts/command_forms.py` — the PLAN-07 lookup D2 consumes
- `manage-metrics/scripts/manage-metrics.py` — three executed render templates that still stated the
  wire/pricing vocabulary as the measure, fixed under the A-condition because D3's worked example
  must equal real render output

⭐ **Both were disclosed** — in the PR body and again in the landing's Residue section, explicitly
labelled *"Recorded surface expansions"*. The second carries a genuine finding with it: the spec's
own premise that *"the scripts already normalized"* was **false for exactly those strings**. A plan
that discovers its spec's premise is wrong, fixes the consequence, and says so is behaving correctly.

⛔ **But disclosure is not declaration, and the gate reads the declaration.** `corpus surfaces`
reports PLAN-12 at **8 claimed entries** — unchanged. The two expansions live in prose only. This is
the exact re-check trigger of the standing in-flight-widening defect, and it is now the **third
consecutive instance** (PLAN-10's D4, PLAN-22's shared helper, and these two) where a plan expanded
its real surface, disclosed it honestly, and left the artefact the disjointness gate consults
untouched. ⚠️ Consequence here is nil — PLAN-12 was the last staged plan, so no sibling could have
collided with it. The pattern is what matters, not this instance.

## ⭐ A conformance lesson shipped as an enforced rule in the same run

`git restore marketplace`, used twice to back out the quality-gate's tree-wide auto-fix churn, also
reverted in-flight D3 render and doc edits living under that tree. Rather than recording that as a
lesson and moving on, the run shipped it as **PR #1461** (`d30496f6e`) into **both versioned
hard-rules surfaces** — `AGENTS.md` and `CLAUDE.md`. Corroborated: `CLAUDE.md` now carries
*"Quality-gate auto-fixes in place — never `git restore` a dirty file to undo it"*, naming the four
rewritten trees and the snapshot-only remedy. The mechanism is real — `build.py` carries the
`ruff check --fix` invocation the rule describes.

⭐ **This is the strongest disposition of a self-inflicted defect in the epic.** A lesson in a report
binds nobody; a hard rule in `CLAUDE.md` binds every future session in this repository. And #1461's
CI exercised the `skip-on-docs-only` path, so the docs-only route was itself confirmed working.

## Metrics and Anomalies

- **Tokens: 45,220,283, population named.** See above. ⭐ Breaks the 11-for-11 lane pattern.
- **Landing amended to revision 3** through the sanctioned `inbox amend` verb: envelope shows
  `revision=3`, `amended=2026-09-10T13:29:24Z`, and `created=2026-09-10T08:47:34Z` **preserved**.
  Validates green. This is the amend surface used exactly as designed — a corrected message
  distinguishable from a virgin one from its envelope alone.
- **Housekeeping owed since the PLAN-11 era is finally discharged.** `/tmp/opencode/main-check` —
  carried as "prunable" in every anchor for eight landings — is **gone**, as are both detached
  `verify-subagent` worktrees. Remaining: `worktree-contract-edits-project-dir-basetemp` (#1445's,
  correctly identified as not this plan's) and `/tmp/opencode/perm-red`. Main at `d30496f6e`, tree
  clean.

## Routing and Merge Behavior

- **Review — both arms handled correctly, and the reasoning is sound.** CodeRabbit's PR-level review
  was present; both findings fixed, thread-replied and resolved, so condition 6 was met via
  `obtained`. Its *incremental* re-review of the review-fix commit was rate-limited (`Reopens? yes`)
  and **not retried, correctly** — the base was unmoved and no further commit was owed, so no
  legitimate new head existed to retrigger with. ⭐ That is the same disciplined reading of the
  no-cosmetic-push rule PLAN-11 applied, reached independently.
- **Sourcery:** rate-limited on #1460 (~4d13h remaining), disclosed before merge, optional, not a
  shortfall. Its budget had reset by #1461, where it reviewed and **approved**.
- **CI/merge:** #1460 merged via the merge queue as `9c23d54e1`; #1461 as `d30496f6e`. Both confirmed
  ancestors of `origin/main`. Branches cleaned up.

## Reconciliation Actions

- [x] row `status` → `landed`; `pr` `#1460`; `landing` `landings/PLAN-12.md`; `plan_marshall_plan_id` `n/a`
- [x] ✅ Open Defect CLOSED — the OpenCode lane's `total_tokens` gap, on the first complete landing
- [x] ✅ Owed housekeeping CLOSED — `/tmp/opencode/main-check` and the verify-subagent worktrees
- [x] Open Defect updated — third consecutive disclosed-but-undeclared surface expansion
- [x] **WS-03 CLOSED**
- [x] resume_anchor updated; START-HERE and Ordered Queue regenerated

## Follow-Ups

- **F1** ⛔ **PR #1445 is still open** — seven landings now. ⚠️ Its subject has been overtaken in
  part: #1461 shipped the quality-gate back-out rule into the versioned surfaces, which is adjacent
  to but not the same as #1445's `--project-dir` and basetemp footguns. Worth re-reading before
  merging, in case it now overlaps or contradicts what #1461 landed.
- **F2** The epic now has **no runnable plan**. Both remaining plans are WS-05 and parked behind a
  live OpenCode install that has never happened.
