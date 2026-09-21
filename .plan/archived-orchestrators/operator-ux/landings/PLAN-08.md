# Landing Analysis — PLAN-08 (remediate-user-facing-sites)

**PR**: #1447 · **Merge commit**: `2ca800212f8ca7de14c00bc8eb2a300d2ee80ac5` · **Workstream**: WS-05-surface-remediation
**Plan id**: `remediate-user-facing-sites` · **Archived at**: `.plan/local/archived-plans/2026-09-08-remediate-user-facing-sites`

## Corroboration

Every material claim below was checked against ground truth before it was recorded here.

| Claim | Verdict | Evidence |
|---|---|---|
| PR #1447 merged | corroborated | `ci pr view --pr-number 1447` → `state: merged` |
| merge sha `2ca800212` | corroborated | `git cat-file -t` → commit; `git merge-base --is-ancestor` → **is an ancestor of origin/main** |
| 26 files changed | corroborated | `git show --stat` → 26 files, +804 / −498 |
| 3/3 deliverables | corroborated | `landing-facts` `deliverables_total=3 deliverables_done=3`; all three surfaces present in the merge |
| landing completeness | corroborated | `inbox landing-check` → `complete: true`, `missing_keys[0]` |
| CodeRabbit reviewed substantively | corroborated | 89 PR comments, real findings per file, each answered and acknowledged; `✅ Addressed in commits 9b61924 to b022ae8` |
| archive-plan record lost | corroborated **and widened** | the archived `status.json` carries the step map but no `archive-plan` row — see Open Defect below |

⭐ **The merge sha is authoritative, unlike PLAN-04's.** PLAN-04's landing named `ef6aff835`, a real
commit that was NOT an ancestor of HEAD (the merge queue's ephemeral commit). This landing named
`2ca800212` and it **is** an ancestor of `origin/main`. The reporting defect did not recur.

## Deliverable fidelity

All three deliverables landed. The plan re-derived its own site list rather than taking the
request's: running the prompt-quality analyzer live produced **11 findings across 5 files from 101
examined prompt blocks**, and only **one** of those five files appeared on the request's original
list. Three sites the request named carry zero structured prompts today because sibling plans
deleted them; they were remediated as prose rather than skipped. That is the emit-time instruction
("its counts are unusable, re-derive from the doctor rule's flagged set") being discharged exactly
as issued — the strongest single outcome of this landing.

## Declared vs realized surface

| Measure | Value |
|---|---|
| Declared entries | 10 |
| Declared **and** realized | **10 — over-declaration 0%, a first for this epic** |
| Realized but undeclared | 16 |
| Under-declaration | **62%** (16 of 26) |

⭐ **Over-declaration reached zero.** Every path the spec declared was touched. No sibling was
serialized behind a file this plan never used.

⛔ **But under-declaration rose (71 / 78 / 67 / 44 / **62**), and the cause is structural, not
random.** The spec declared deliverable 1's surface (10 marketplace prompt files, all realized) and
declared **none** of deliverable 2's — the 10 `doc/user/*.adoc` files the plan's own Goal names
explicitly. The remaining 6 undeclared entries are genuine discovery (`architecture-setup.md`,
`menu-maintenance.md`, `menu-terminal-title.md`, `finalize-step-sync-baseline.md`,
`output-template.md`, and the new smoke test). So this is not a spec that under-estimated its
reach; it is a spec that declared one deliverable's surface and omitted another's entirely. The
44% → 62% move is therefore **not** a regression in declaration discipline — it is one deliverable
never having been declared at all, which a per-deliverable surface check would have caught and an
aggregate percentage cannot see.

## Metrics

21h14m wall / 6h41m worked / 14h33m idle · 9.51M tokens · 2551 tool uses · 176.3M billing units.
Phase 5 re-entered; `loop_back_iterations=6`. Phase 6 alone consumed 5.94M tokens (62% of the plan)
across 1220 tool uses — the most expensive finalize in the epic, driven by the 7 self-review firings
and the CodeRabbit round-trips.

## Routing / merge behaviour

Merged through the platform merge queue, 11 commits, `upstream_commit_count=3` at branch-cleanup.
One genuine CodeRabbit rate-limit window cost a single 90-minute wait of the ten authorised. One
apparent refusal was adjudicated a false positive on four independent signals. `cuioss-review-bot`
was re-triggered directly after going stale. `review_decision: none` on the PR — the same surface
signature as PLAN-02's defect — but here it is a GitHub artifact, not an absence of review: three
reviewers participated and 23 actionable comments were compared.

## Reconciliation actions

- Queue row PLAN-08 → `shipped`; `pr`, `landing`, `plan_marshall_plan_id` stamped.
- 12 inbox messages drained: 10 promoted, 1 discarded as a recurrence, 1 reconciled (this landing).
- 10 lessons filed as `2026-09-08-13-002` … `-011`.
- Recurrence #2 recorded on existing lesson `2026-09-07-15-002`.
- Two Open Defects added (below); no Watch retired.

## Defects this landing surfaced

**1. The archive-plan completion record is lost on 85% of all plans, not on this one.**
The plan reported its red row as a self-inflicted ordering slip. A scan of every archived plan
says otherwise: **17 of 20 archived plans carry no `archive-plan` row**, while carrying the rest of
the step map and, in 17 cases, the immediately-preceding `emit-landing` row. Only 3 recorded it.
The standard is unambiguous — `archive-plan.md` line 52 states the `mark-step-done` call MUST
precede the archive and explains the exact failure — and it is violated anyway, at scale, across
many plans and three weeks. This is the case for moving the constraint out of prose and into
`manage-status archive`, which is what lesson `2026-09-08-13-001` proposes; the scan that lesson
suggested as optional is what converts a self-blamed one-off into a measured systemic defect.

**2. The emit-time `.adoc` instruction was not discharged, and the blind spot is still open.**
The emit required PLAN-08's outline to "either confirm the gap is fixed or state it in its own
report." The report does neither. The gap is confirmed still open at HEAD: no `.adoc` detector
exists anywhere under `ext-self-review-plan-marshall`. So `pre-submission-self-review clean: 147
candidates examined, no check matched` covers the marketplace half only — **all 10 shipped
`doc/user/*.adoc` files were structurally invisible to it**, and that is deliverable 2 in its
entirety. What actually reviewed them was CodeRabbit, which filed findings on `commands.adoc`,
`configuration.adoc` and `getting-started.adoc`. The AsciiDoc half of this plan was covered by an
external reviewer rather than by the instrument the plan reported clean.
