# Landing Analysis: PLAN-06 — Honour the user's language, and speak the user's vocabulary

epic: operator-ux
workstream: WS-04-how-plan-marshall-talks
pr: #1382 — https://github.com/cuioss/plan-marshall/pull/1382

> Landing record for one shipped plan. Lives at `landings/PLAN-06.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Ground truth: `ci pr view --pr-number 1382` returns `state: merged`,
`merge_commit_sha: 219da7b1dbbd73ee4cf74df4d3c09c2e27ecbc52`; `git merge-base` confirms it is
in `main`; `git show --stat` reports **13 files, +674 / −40**.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1. New `standards/user-communication.md` + **unconditional** load step | shipped-as-specified | File created; `SKILL.md` Step 1 is retitled "Load Core Development Rules **and User-Communication Rules**" and states "Neither is optional and neither is loaded on demand — they are the unconditional tier" |
| 2. User-language rule with scope and non-scope | shipped-as-specified | In `user-communication.md`; resolution order via `project.user_language` |
| 3. `marshal.json` user-language knob + `manage-config` surface | shipped-as-specified | `project.user_language` (default `auto`), guards on both halves of the read/write boundary, `test_user_language_knob.py` |
| 4. User-vocabulary rule + displacement glossary | shipped-as-specified | Glossary present per `SKILL.md` standards-reference row |
| 5. Boundary: rename for the user, never in the code | shipped-as-specified | Scope/non-scope stated in the standard |
| 6. Pointer from `agent-behavior-rules.md`, no rule text duplicated | shipped-as-specified | That file is in the diff at +/− consistent with a pointer edit |

**The load-bearing constraint held.** The spec carried an explicit ⛔ that the new file must
join the UNCONDITIONAL tier, because the "as needed" tier would reproduce the opt-in failure
that got a standalone skill rejected. It landed at Step 1, and the SKILL.md prose now states
the non-optionality in its own words. This is the deliverable the whole placement decision
rested on.

### Under-declaration: 4 of 13 files (31%)

Declared 7 entries; realized 13. **A marked improvement on PLAN-01's 71%**, and the
`test/plan-marshall/manage-config/` directory declaration correctly absorbed three test files.

| Undeclared file | Note |
|---|---|
| `doc/user/configuration.adoc` | **Operator-caused, not drift** — the operator overrode the defer-to-`data-model.md` argument to put the knob in the user-facing guide |
| `manage-config/standards/api-reference.md` | Contract surface adjacent to the declared `SKILL.md` |
| `manage-config/scripts/_cmd_system_plan.py` | The knob's read/write implementation |
| `manage-config/standards/provisioning-fail-closed-audit.md` | Audit doc touched by the new knob |

No spec's declared surface was invaded, so no sibling correction is owed. Recorded because the
realized-vs-declared ratio is now a standing field in these reports.

## Metrics and Anomalies

- Tokens: 6,683,572 — **the epic's most expensive plan by 45%**. Duration 4h53m worked /
  15h4m wall. 6-finalize alone: 4,315,774 (65%).
- **Anomaly — the 2.5× overrun is structural, not incidental.** Each loop-back fix advanced
  HEAD, invalidating every head-dependent gate, so two loop-backs cost three full settle-band
  passes. This is a re-entry amplification property of the finalize design, not a plan defect.
- **Anomaly — review coverage was thinner than the quorum reported.** 3/3 is *participation*,
  not coverage: the required bot published empty, and Sourcery is out of budget yet credited as
  participating because its refusal wording is not in its own patterns. Real coverage was
  CodeRabbit alone. Six self-review rounds found three defects the bots structurally could not.
  ⛔ Second independent instance of `2026-09-02-08-001`, already recorded by the run's own
  review-retrospective; deliberately not re-filed here (one observation, one record).
- **Anomaly — the session that judged this run read the PRE-change persona** (cache at
  0.1.1581). The plan's own rules were not in force for the agents evaluating it. Recorded as
  lesson `2026-09-03-06-005`.

## Routing and Merge Behavior

- Merged via the queue as `219da7b1`, all checks green, no rebase conflicts.
- **Surface-collision check: the gate predicted correctly.** PLAN-06 ran alone by construction
  (every candidate collided with it on `manage-config/SKILL.md`), and its realized footprint
  confirms that file was indeed touched — the serialization was real, not a false positive.
- Two operator decisions shaped the deliverable: choosing ASCII-transliteration over
  English-with-jargon-stripped (turning Rule 1a into a worked rule with a non-Latin-script
  fallback rather than an exemption), and overriding the defer argument to put the knob in the
  user-facing config guide.

### ⛔ Open defect carried: `status.json` records `5-execute` as `in_progress`

The loop-back mechanism uses `set-phase`, and the resumed dispatch yielded `blocked` rather
than self-transitioning, so no `transition --completed` fired. The executor **could not**
correct it post-merge: the phase-entry worktree assertion refuses because `branch-cleanup`
already removed the worktree — and it **declined to clear that metadata to get past a safety
guard**, which is the correct call. The metrics ledger is right (`close_count: 2`, `end_time`
present, no missing boundaries); only the status row disagrees, and it is logged.

**This is the SECOND instance of one root cause**, and that is the finding rather than the
symptom. PLAN-01 hit the same wall from a different direction: its pre-archive findings-check
could not run because `metadata.worktree_path` named a worktree `branch-cleanup` had removed.
⛔ **Any post-`branch-cleanup` operation gated on the phase-entry worktree assertion is
unrunnable by construction** — two independent symptoms, one ordering defect. Promoted from a
single-instance defect to a confirmed class in the epic ledger.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-06 --status shipped`
- [x] row `pr` stamped — `#1382`
- [x] row `landing` stamped — `landings/PLAN-06.md`
- [x] row `plan_marshall_plan_id` stamped — `user-language-and-vocabulary`
- [x] 9 inbox messages drained, each dispositioned and archived
- [x] 7 new lessons promoted; 5 recurrence sections folded onto existing corpus entries
- [x] Epic Open Defect upgraded — post-`branch-cleanup` worktree assertion, now 2 instances
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- **PLAN-07 is now unblocked** — it appends to the `user-communication.md` this plan created.
- **Five simultaneous recurrences, none with a landed remedy** (`2026-08-25-09-001`, `-008`,
  `-009`, `-014`, `2026-09-02-13-005`). The plan's own message asks whether that is "itself a
  scheduling signal for the epic". It is, and it is recorded as a watch: this epic is
  accumulating finalize-machinery debt faster than it is retiring it, and none of that debt is
  operator-UX work. It belongs in a separate epic, not folded here.
- **Lesson `2026-09-03-06-004`** (a runtime instruction to use Bash for file operations does
  not override the hard rule) is directly relevant to this epic's own working conditions and is
  worth applying, not merely filed.
