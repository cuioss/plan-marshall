envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T13:46:51Z

component=plan-marshall:phase-6-finalize
category=bug

# architecture-refresh commits a descriptor-format migration into an unrelated plan's PR, and that self-commit trips push's freshness gate

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, drain of plan
`lessons-handling-epic-residual-cleanup` (PR cuioss/TokenSheriff#744, 2026-09-15). **Bundles two
inbox messages** (`-003` freshness gate, `-007` descriptor churn) because both come from the same
commit `bfcbc925`. The orchestrator checked the merged diff and the cited log entries before relaying.

## Observation 1: format migration rides a plan PR

On plan-marshall 0.1.1670, the finalize `architecture-refresh` step rewrote committed
`.plan/project-architecture` descriptors in the consumer repo. **Verified on the merged squash
commit `7f7edc4b`:** 16 of the PR's 20 files are descriptors (`_project.json` plus 15
`enriched.json`). `enriched.json` `key_packages` keys changed from Java package names to source
paths (for example `"de.cuioss.sheriff.token.validation"` became
`"token-sheriff-validation/src/main/java/de/cuioss/sheriff/token/validation"`), and a
`generation: {by: architecture, tree_sha: null}` stamp was added. No module was added or removed
(work.log `ca39db`: "0 added / 0 removed (descriptor format drift …)").

The plan changed 4 files; its PR changed 20. The repo's steward upgrade to 0.1.1670 had landed
separately the same morning (#743), but it did not migrate the descriptors, so the migration fell
to the next plan.

## Observation 2: the self-commit makes push report stale

`architecture-refresh` runs after the last verified build and commits. It is not declared
`mutates_source`, so no freshness-reconcile record is written. push's freshness gate then sees
HEAD past the last verified build and refuses with `stale / worktree_mutated`. The operator forced
it (decision.log `6b23b1`: "self-committed bfcbc925 (.plan/project-architecture JSON only, not a
Maven build input) after the last successful verify -Ppre-commit at HEAD e743abe5").

## Why it matters

One step both widens a plan's realized footprint by 4× with unrelated churn and manufactures a
false-stale freshness verdict whose only exit is `--force`. A `--force` habit hides real staleness.

## Candidate direction

- Land descriptor format migrations once, through the upgrade path (`/marshall-steward upgrade`),
  not as a side effect of whichever plan finalizes next.
- Either `architecture-refresh` writes a freshness-reconcile record for its own descriptor-only
  commit, or the freshness gate treats a commit touching only `.plan/project-architecture/**` as
  build-neutral.
- Check that rekeying `key_packages` from package names to paths is intended for Java modules.
- Related, distinct mechanisms: `-038` (diff-modules false positive on a byte-identical
  baseline), `-051` (`plan=NO_PLAN` build rows making freshness stale).
