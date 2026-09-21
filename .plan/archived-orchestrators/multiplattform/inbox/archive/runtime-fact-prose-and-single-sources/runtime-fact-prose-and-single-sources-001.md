envelope_version=1
sender_type=plan
sender_id=runtime-fact-prose-and-single-sources
epic=multiplattform
kind=landing
created=2026-09-09T15:40:00Z

```landing-facts
schema=landing-facts/1
plan_id=runtime-fact-prose-and-single-sources
epic=multiplattform
pr=#1458
merge_state=merged
deliverables_total=5
deliverables_done=5
total_tokens=unknown
steps=step-4-implement:done,step-5-build-gate:done,step-6-verifier:clear,step-7-pr:done,step-8-merge:done,step-9-self-check:done
```

## Residue

- **`total_tokens=unknown`**: the opencode session could not report a token total; routed to `unknown` per the landing contract (never `n/a`).
- **Sourcery review rate-limited** on diff size (>150,000 chars, `Reopens? no`): optional reviewer, disclosed to the operator before merging; not a shortfall.
- **Step 5 gate environment note**: the gate initially failed on a pre-existing stale `argparse_surface` on-disk help-cache in the main checkout (build-server-client `submit --timeout` surface derived without it — reproduced identically on pristine main, so not a branch defect); cleared, no source change. The daemon-mode gate cannot build a worktree project-dir on this host (`pwx` wrapper unresolved there); the gate was run via `--execution-mode in_process` (same `pw verify`), green. CI verify green on the merged head.
- **17 CodeRabbit review comments dispositioned**: 11 fixed (incl. a real `--scope` save bug in permission_fix, a gitignore legacy-header migration, and a repr serialization fix in generate_executor), 6 replied-with-reason on their threads (target-awareness of layout ops, effort single-sourcing = the recorded marketplace/targets proposal, etc.).
- **D4 recorded proposal**: the LEVEL_TABLE/model_map cross-target single-sourcing is recorded as a `marketplace/targets` proposal in `effort-levels.md` — out of this plan's surface.