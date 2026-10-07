envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=landing
created=2026-08-09T17:04:41Z

## What landed

**PLAN-PR-022** — *a generic charter cannot see a language-specific defect* (WS-03) — landed as **PR #1130**, merged via the merge queue, squash commit `f5493b437`. Plan id `generic-charter-language-specific-defect`.

The host-repo half of eight deliverables shipped: a third generator target (`pr-agent`) registered in `TARGET_REGISTRY`, the `_INFRA_CONFIG_BASENAME_GLOBS` classifier widened by the review-bot descriptor family (`.pr_agent.toml`, `.coderabbit.yaml`, `.coderabbit.yml`), `participation_evidence` for pr-agent widened with `inline` (appended AFTER `issue_comment` so `participation_evidence(bot)[0]` stays stable for the seven modules that read it), and the emitted agents file renamed to `AGENTS.md` across the command doc, `marshall-steward/scripts/determine_mode.py`, and the two pinning test modules.

23 of 23 declared host-repo paths landed (100% recall), plus 5 undeclared files. Whole-tree quality-gate, test-compile, and 18,135 module tests green; plugin-doctor 31 rules / 0 findings.

## Two baked-in refutations held

The spec's two refutations were carried through implementation unchanged and are now first-party settled, not merely asserted:

- `reasoning_effort` is dead config for Gemini (`SUPPORT_REASONING_EFFORT_MODELS` is o3/o4 ids only) yet still appears in every resolved-config dump — so "set effort high" remains non-executable as config.
- Charter packs are **selected and swapped** via repo-local `.pr_agent.toml` with `use_repo_settings_file: true`, not appended, because the org charter was already at nine categories against the ">10 categories → a second focused pass" rule.

## Residue the epic must track

**1. Three foreign-repo deliverables are complete-but-UNLANDED.** D6 (`cuioss-organization`), D7 (`pr-agent-settings`), D8 (`API-Sheriff` + `TokenSheriff`) were implemented, committed, and pushed in four foreign checkouts. Verified at finalize: every branch is in sync with its origin, each commit is contained by its feature branch only, and `ci pr list --state open` returns **zero** PRs for any of the four branches. Tasks 9/10/11 all reported `done`. This is sent in full as `candidate-lesson` message `-001`; recorded here so the landing itself is not read as "PLAN-PR-022 shipped end-to-end". **PLAN-PR-004 absorption cannot be judged until D6 actually lands.**

**2. The merge was authorized over a vacuous quorum.** `barrier-ask-override` was granted at HEAD `c30d5a656` on gap class `participated_but_empty`: pr-agent participated with 0 actionable comments, coderabbit `refused_awaitable` (rate window, `review_rate_window_await` off for this plan), sourcery `refused_hard` (quota). `unproven_bots=[coderabbit, sourcery]`. **No external reviewer produced content on this 27-file diff.** The operator was shown the gap explicitly and chose to proceed on in-house evidence. Sent as `candidate-lesson` message `-008`; it is fresh first-party evidence for PLAN-PR-008, PLAN-PR-021, and PLAN-PR-011, not a new plan.

**3. Three distinct script notations were argparse-rejected inside this run's finalize phase** — `manage-architecture:architecture`, `manage-status:manage-status`, and `tools-integration-ci:ci`. Sent as `candidate-lesson` message `-007`. This is direct reinforcement for **PLAN-PR-017**, and it adds a sub-signature that plan's current framing does not cover: for `architecture`, the flag IS declared (top-level) and the rejection banner **advertises it in the usage line it prints while rejecting it**.

**4. The forwarded signal counts disagreed with the records again — third instance.** `signal_script_failure_clusters_count: 1` was forwarded against **3** distinct failing notations in the work log; `signal_qgate_pending_count: 5` was forwarded against **11** Q-Gate findings across 3-outline (6), 4-plan (1), and 6-finalize (4), all of them resolved. This is the same arithmetic defect the drain already delegated to `truthful-signals` as `review-apparatus-019.md`. **Nothing is owed back to this epic** — recorded here only as corroboration that the defect is live and reproduces per-run, not as a new item for this ledger.

**5. Plugin-cache marker survey failed the single-unmarked-dir assertion at finalize.** Double-sampled 14s apart, both samples agreeing (so determinate, not a read-during-write): 12 version dirs, **two** unmarked — `0.1.1331` and `0.1.1334`. The executor was regenerated at `0.1.1334`; this session had loaded its skills from `0.1.1327`, now orphan-marked. No registry pin file was found at any of the five probed locations, so the loader follows an ambiguous unmarked set. Repair is operator-only, and a full session restart (not `/reload-plugins`) is what re-seats skill markdown. **Not a review-apparatus subject** — recorded so a later reader of this landing knows which cache generation produced it.

## Queue action requested

Transition `PLAN-PR-022` from `running` to `shipped` and stamp the row: `plan_marshall_plan_id=generic-charter-language-specific-defect`, `pr=1130`. The landing report is owed at `landings/PLAN-PR-022.md`. **The slot frees only if residue item 1 is accepted as out-of-band** — three deliverables of this plan have no pull request in any repository.
