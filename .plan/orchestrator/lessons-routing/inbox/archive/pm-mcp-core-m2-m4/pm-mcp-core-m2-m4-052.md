envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:15Z

# Push the sibling-repo docs branch and open its pull request in finalize

## Context

PLAN-06 had four documentation deliverables (D1, D11, D12, D13) in the sibling repository
plan-marshall-documentation. The standing constraint of the epic requires a documentation pull
request there. After the code pull request #26 merged (cbdd04e), the docs work is committed only on a
local branch: `feature/plan-06-store-substrate` at 7d0d1c0 (commits b4d886e, a3f97af, d74ce90,
7d0d1c0), with no upstream, in the worktree `.plan/temp/plan-06-plan-marshall-documentation` of the
main checkout. No finalize step pushed it or opened the pull request; create-pr only mentioned it as
"follows this one".

## Root cause

The phase_6 step list (sync-baseline, pre-push-quality-gate, push, create-pr, ci-verify,
automatic-review, sonar-roundtrip, branch-cleanup, ...) acts on the plan's own repository only. A
deliverable whose module is a sibling repository has no finalize step that owns its branch.

## Proposed action

Either add a finalize step (or a create-pr sub-branch) that, for every deliverable whose module is a
declared sibling repository, pushes that repository's plan branch and opens its pull request with the
body the plan specifies; or make finalize refuse to report done while such a branch exists unpushed
and surface it to the operator. For PLAN-06 itself: push `feature/plan-06-store-substrate` in
plan-marshall-documentation and open the docs pull request (coverage table, requirement corrections
of D1, remaining items); the operator merges it.

## Evidence

- aspect: request_result_alignment - D1, D11, D12, D13 partial; docs branch has no upstream
- aspect: chat_history_analysis - create-pr leaf: "documentation PR ... not yet pushed ... follows this one"
- git: `for-each-ref refs/heads/feature/plan-06-store-substrate` in plan-marshall-documentation shows no upstream

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-06-store-substrate-010.md` from plan plan-06-store-substrate (PLAN-06, #26)
