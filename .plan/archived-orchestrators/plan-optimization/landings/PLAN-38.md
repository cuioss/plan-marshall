# Landing Analysis: PLAN-38 — Domain-Ambiguity Candidate Set

epic: plan-optimization
workstream: WS-10
pr: #975 (`9ac2601e8`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Verified against merge commit `9ac2601e8` (4 files, +189/-15). **2/2 shipped** (the staged D1
gate + D2/D3 collapsed to 2 as executed: the fix and its contract alignment).

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — offer configured-but-unmatched domains on every ambiguous branch | shipped | `_cmd_domain_detect.py` (+80): the multi-match branch now offers the detected candidates **plus** the remaining configured non-system domains, presented as a second group (the operator's "as WELL", not a peer flatten) |
| D2 — align the phase-1-init Step 7 prompt contract | shipped | `phase-1-init/SKILL.md` (+12), `manage-config/SKILL.md` (+4), `test_cmd_domain_detect.py` (+108) |

## ⚠ The D1 hypothesis CONFIRMED — but the mechanism was sharper than staged

The spec's D1 was: *"HYPOTHESIS — the fix site is the detector's `candidates` construction, not
the phase-1-init prose."* Confirmed. But the finding is **more specific than the hypothesis
stated**, and this is the valuable part:

> The widening to "all configured non-system domains" **already existed in the script — but only
> on the zero-match branch.** The defect was a **script-side asymmetry between two branches of the
> same function**, not a missing capability.

So the fallback wasn't merely "on the wrong branch" as I framed it — it was *present and working*
on one branch and *absent* on the sibling branch of the same function. The fix was to make the two
branches symmetric, not to build new capability. **This is the fourth-plus consecutive landing
where the artifact read at D1 sharpened (not overturned) the staged mechanism** — the binding
practice continues to pay in precision even when the hypothesis holds.

## ⚠ Two unpredicted defects, BOTH in the offer surface the plan owns

Neither was in the spec — both surfaced during execution, in exactly the surface the plan touched.
This is the **`guards-are-highest-risk-artifact` shape reappearing as `offer-surface-is-highest-
risk`**: the code the plan changes is where its own new defects concentrate.

1. **`active_profiles` leaked as a selectable domain.** A live smoke test showed `active_profiles`
   — a bookkeeping list stored *alongside* the domain entries in `skill_domains` — being offered
   as a domain. **The pre-existing zero-match branch had the same leak** (so the plan's new group
   inherited a latent bug from the branch it was mirroring). Fixed in both via the `isinstance(dict)`
   guard the narrative loop already used. **Note: this means the *original* zero-match prompt has
   been offering `active_profiles` as a selectable domain all along — a pre-existing consumer-facing
   defect this plan incidentally cleaned up.**
2. **Placeholder-shape mismatch (CodeRabbit).** `{candidate_1}` interpolates an object while the
   adjacent new `{additional_1}` is a bare string — identical placeholder shape, different element
   types. **Adding the second group is what made the pre-existing loose placeholder misleading** —
   a latent ambiguity exposed by new adjacency, the same pattern as PLAN-31's contract-sentence
   defect. Fixed; lesson `2026-07-22-10-001`.

## Metrics and Anomalies

- Tokens: **1.9M** · Worked: **29m55s** · Wall: **2h12m**
- ⚠ **19m idle in 5-execute was two DEAD dispatches.** Two consecutive execution-context
  dispatches died with `API Error: Connection closed` mid-response (~170s, ~108s), zero disk
  progress. The plan **verified the worktree was clean both times rather than blind-retrying**,
  then drove phase-5 inline. Recurrence of lesson `2026-07-21-16-004`. **This is the same
  dispatch-instability class the epic has hit repeatedly** — the correct disposition (verify disk,
  drive inline) is now well-established, but the underlying instability is unowned.
- Deploy: 1110 files, bundles **0.1.1186**; executor regenerated.

## Routing and Merge Behavior

- **Review**: 2 CodeRabbit comments (1 fixed, 1 taken into account). But see the review-surface
  finding below.
- **CI/merge**: all green, merged via queue, `main` at `9ac2601e8`, worktree removed.
- **Surface collisions**: none. The `manage-config` cross-awareness with PLAN-37 held — PLAN-38
  touched `_cmd_domain_detect.py`, PLAN-37 owns `_config_core.py`/providers, no overlap.

## ⚠⚠ Cross-cutting finding: the review surface is 1 bot, not the 3 configured

`enabled_bots` names **coderabbit, sourcery, gemini** — but only **CodeRabbit** registered a
check-run. Sourcery reported `SKIPPED`, Gemini nothing at all. Everything worked because
`bot_completion` correctly distinguishes structurally-absent from in-progress (the PLAN-21
hardening holding) — **but the project is getting one-third of the review coverage its config
implies.**

This is bigger than one plan. Two of this epic's standing observations converge here:
- **Gemini has produced real findings on n=7 consecutive landings** — yet it is apparently *not
  actually running* as a check-run. If those n=7 findings came through a different channel (PR
  comments not check-runs), the "gemini still works despite sunset" watch may have been measuring
  a channel that is itself now degrading.
- **Sourcery SKIPPED silently.** A bot in `enabled_bots` that never runs is a config-vs-reality
  drift — the same class as PLAN-37's credentials-key drift and the roster-count drift PLAN-36
  fixed: **the declared set and the operative set have diverged, silently.**

## Reconciliation Actions

- [x] status.json `plans[]` updated (`shipped`, pr `975`, landing `landings/PLAN-38.md`)
- [x] epic.md queue row reconciled
- [x] Watch `ambiguity-prompt-narrow-candidates` — RETIRED (PLAN-38 D1 #975)
- [x] New watch: **enabled-bots-vs-operative-bots drift** (sourcery SKIPPED, gemini absent as
      check-run) — folds the `gemini n=7` watch into a sharper question
- [x] New watch: **dispatch-instability unowned** (lesson `2026-07-21-16-004` recurring, cost 19m here)
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **⚠ Review-surface audit owed.** Confirm whether gemini/sourcery are actually running and via
  what channel. If two of three configured bots are silently absent, the `enabled_bots` config is
  lying, and either the bots need re-enabling or the config needs pruning to match reality
  (per the infra-steps-opt-in principle — a listed bot that never runs is worse than an honest
  two-bot config). **Candidate plan; not staged (four running).**
- **Dispatch-instability is now the epic's most expensive recurring tax** — verify-disk-then-inline
  is the right response but it is a workaround, not a fix, and the cause (harness/API connection
  drops mid-dispatch) is unowned by any epic. Worth surfacing to the operator as an infrastructure
  item beyond plan-marshall's code.
- **`/marshall-steward` owed** — provisioning stamp was stale at session start (0.1.1180 vs
  0.1.1184) and this plan bumped to **0.1.1186**. The executor regenerated on main, but the config
  seed stamp lags. This is the same provisioning-stamp lag cleared earlier in the session; it has
  re-accrued across the day's bundle bumps.
