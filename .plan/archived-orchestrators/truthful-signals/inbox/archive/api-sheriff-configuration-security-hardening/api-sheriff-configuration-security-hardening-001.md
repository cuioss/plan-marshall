envelope_version=1
sender_type=plan
sender_id=api-sheriff-configuration-security-hardening
epic=truthful-signals
kind=finding
created=2026-09-15T17:20:00Z

component=plan-marshall:phase-6-finalize
category=bug

# `architecture-refresh` Tier 0 wants to commit plan-unrelated descriptor churn into the plan's PR, and the regression gate calls it benign — including a `key_packages` re-keying from Java package names to directory paths

⛔ **OBSERVED IN A CONSUMING REPO (`cuioss/API-Sheriff`), plan `configuration-security-hardening`
(PLAN-25 of the `deployment-configurability` epic), finalize step `default:architecture-refresh`,
2026-09-15.** Filed by operator direction. The churn was **reverted, not committed**, so the PR stayed
focused — the defect is that the step as documented would have shipped it.

## What happened

At plan-marshall `0.1.1670`, worktree HEAD `8e21dff` (branch rebased onto `origin/main` `fb9e774`):

1. `architecture --project-dir {worktree} discover --force` → `modules_discovered: 10`.
2. `diff-modules --pre {origin/main baseline}` → `added[0]`, `removed[0]`, `changed[10]` (the
   documented derived-less-baseline noise).
3. `git status --porcelain .plan/project-architecture` → **8 files dirty** (57 insertions, 15 deletions):
   `_project.json` plus seven `*/enriched.json`.
4. `descriptor-regression-check --pre {baseline}` → `regressive: false`, `violations[0]`.

Per `phase-6-finalize/standards/architecture-refresh.md` § 3c.5 / 3d, a non-empty porcelain plus
`regressive: false` means **commit** (`chore(architecture): refresh derived data after …`) onto the
plan's feature branch, and `default:push` ships it in the plan's PR.

## The churn, and why none of it came from the plan

The plan changed Java sources, tests, a JSON schema and AsciiDoc — **no module was added or removed and
no descriptor input changed**. The regenerated delta was entirely tool-side:

- **Every module entry in `_project.json`** (and a matching +4 lines in six `enriched.json` files):
  `"generation": {}` → `"generation": {"by": "architecture", "tree_sha": null}`. A provenance stamp
  whose `tree_sha` is `null` records that the generation happened but not against what — the
  confident-but-empty shape.
- **`api-sheriff/enriched.json` `key_packages` re-keyed.** Three curated entries moved from Java package
  keys to directory-path keys with byte-identical descriptions:
  `de.cuioss.sheriff.gateway.config` → `api-sheriff/src/main/java/de/cuioss/sheriff/gateway/config`
  (likewise `…config.model` and `…tls`). Every other `key_packages` entry in the same object kept the
  package-name form, so one map now mixes two key vocabularies.

## Why this is a truthful-signals defect, not just noise

- **`descriptor-regression-check` is scoped to project identity only** (`name`, `description`,
  `description_reasoning`). A re-keying that changes the addressing vocabulary of curated enrichment
  data is invisible to it, so `regressive: false` reads as "safe to ship" over a change the predicate
  never examined. The gate's green is narrower than its name.
- **The commit gate is on-disk dirtiness, not plan-caused change.** A plan-marshall upgrade between the
  last committed refresh and this plan is enough to make *every* plan's finalize carry the upgrade's
  descriptor churn — attributed, in the commit subject, to the unrelated plan ("refresh derived data
  after {plan-title}").
- **It collides with consumer policy.** API-Sheriff's `CLAUDE.md` § Pre-Commit Process: a gate run can
  change files; "Revert unrelated churn; keep the rewrite only for files the branch itself authored."
  The step prescribes the opposite for this class.

## Suggested direction (not verified upstream — no plan-marshall source was read for this finding)

- Scope the Tier-0 commit to deltas attributable to the plan (e.g. only when `added ∪ removed` is
  non-empty, or when the plan's footprint touches descriptor inputs), and route pure tool-version
  churn to a separate steward reconcile instead of the plan PR.
- Widen `descriptor-regression-check` (or add a sibling) to flag `key_packages` key-vocabulary changes
  and `generation.tree_sha: null` stamps, or state in its output which fields it examined so a
  `regressive: false` cannot be read as whole-descriptor assurance.
- Confirm whether the package-name → path re-keying is intended in `0.1.1670`'s enrich/discover code
  path; if intended, it should arrive via one reconcile commit across all modules, not piecemeal.

## Minor, same step, same run

- `architecture-refresh.md` § 2b prescribes `rm -rf {worktree}/.plan/temp/architecture-baseline …` as a
  plain Bash call; in this session the harness denied it (permission prompt refused), so the documented
  "clear any previous extraction" step is not reliably executable. An executor verb (or a
  `manage-files`-style cleanup) would make it deterministic.

— source: API-Sheriff plan `configuration-security-hardening` finalize, decision log entry
`(plan-marshall:phase-6-finalize:architecture-refresh) Tier 0 — discover --force produced unrelated
descriptor churn …`, 2026-09-15.
