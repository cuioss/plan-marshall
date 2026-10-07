envelope_version=1
sender_type=plan
sender_id=audit-report-path-ignores-plan-dir
epic=code-intelligence-substrate
kind=landing
created=2026-07-30T08:05:20Z

## What landed

**PR #1063** — `audit-report-path-ignores-plan-dir`, 4 commits.

| Commit | Deliverable |
|--------|-------------|
| `225f3be9` | **D1** — repo-root resolution follows ADR-002: cwd walk-up installed at `audit.py` `main()`:7065, plus 3-branch resolver tests (mutation-verified) |
| `2a471ae2` | **D2** — derived shipping predicate; `DELIVERY_COST_CHECKS` / derived `FULL_CORPUS_CHECKS` partition; exclusion accounting |
| `de6eb8be` | **D3** — doc port to `SKILL.md` + 8 `checks/*.md` |
| `2475cd17` | loop-back fix from a CodeRabbit finding: lock-step test extended to guard the `SKILL.md` table (mutation-verified) |

## Substantive corrections to the spec

- **The spec's hypothesis was REFUTED.** `write_persisted_report` never called `Path.cwd()` — it takes `repo_root` as a parameter. The sole cwd-dependent site was `main()`:7065, and that one value threads into **six** consumers, so the real blast radius was far wider than the reported "report path". The named location was a sample of the defect, not the defect.
- **D3's sibling sweep resolved to "none found" by enumeration**, not by assumption: five widened patterns were checked (`Path.cwd`, `os.getcwd`, `Path(".")`, `Path("")`, bare relative I/O). `os` is never even imported in the module.
- **Column-name collision resolved by operator decision**: the new column is `excluded_non_shipping_plan_ids`, because `exploration-share` already owns `excluded_plan_ids` for an unrelated exclusion. Two different exclusions must not share a column name.

## Residue the epic should track

1. **The final shipped commit (`2475cd17`) was reviewed by nobody.** The plan's review-retrospective recorded this explicitly. A loop-back commit that fixes a bot's own finding is not re-reviewed by default; Trigger B re-triggers only the most-recently-reviewed bot, so the required bot (pr-agent) never saw the shipped tree. Filed as a candidate-lesson on this queue.
2. **`resolve-test-scope` returns a docs-only verdict (`recommended_target: null`) for changed paths under `.claude/skills/**`**, which `execute-task` reads as "run no pytest" — a false negative for Python source living in project-local skills. This was hit during this plan's execution. It is **already filed as a finding to the `truthful-signals` epic** (operator-directed cross-epic routing) and is deliberately **not** re-filed here — noted only so this epic knows the exposure exists on its own audit surface.

## Candidate-lessons emitted alongside this landing

Three, each as its own `candidate-lesson` message: reported-location-is-a-sample; review-bot participation is per-commit; phase-5-tail build-stamp staleness is structural.
