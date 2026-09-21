envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=landing
created=2026-08-09T20:34:30Z

# PLAN-TRUTH-070 landed: runtime edge paths that crash or silently lose data

## What shipped

PR **#1132**, merged through the GitHub merge queue as squash commit
`ff4462148c9f2baf499c2028ff9b3f5fbaedb1ee` on `main`. Branch
`feature/runtime-edge-paths-crash-or-silently-lose-data`, 15 files in the landing commit.

All six staged defects plus the sweep deliverable:

| Ref | Defect | Component |
|-----|--------|-----------|
| R5 | `get_metadata_content_split` returned overlapping metadata and body for all-metadata content | `tools-file-ops` |
| R6 | Bulk finding-resolve wrote `resolution_detail: None`, erasing stored detail on every bulk resolve | `manage-findings` |
| R10 | Root-module path collapsed to `''`, so downstream `startswith`/`==` matched everything | `manage-architecture` |
| R10b | `lstrip('./')` retired marketplace-wide as a prefix-strip (it is a character set, not a prefix) | cross-cutting |
| R2 | `Retry-After` as an HTTP-date raised an uncaught `ValueError` out of the REST retry loop | `manage-providers` |
| R3 | Empty basic-auth password base64-encoded a half-configured header instead of being rejected | `manage-providers` |
| R7 | `compute_total_elapsed` subtracted outside its `try`, so a naive/aware mismatch raised `TypeError` | `tools-integration-ci` |

D8 held: one regression test per finding, each **empirically observed failing against pre-fix
source** rather than asserted to fail.

## Two landing facts the epic should keep

**1. The spec's own re-verification was stale, and the population-derived sweep is what caught it.**
The plan spec asserted the six `lstrip('./')` sites in `opencode/plugin_discover.py` "are now gone"
and carried the HYPOTHESIS that the sweep would find no further sites. The population-derived guard
(`test/marketplace/test_prefix_strip_idiom_retired.py`, scanning 409 files) failed pre-fix naming
**three** offenders — `manage-architecture/scripts/_cmd_manage.py`,
`pm-plugin-development/.../plugin_discover.py`, and `marketplace/targets/opencode/emitter.py`. So
`plugin_discover.py` was **not** clean, and the spec's re-verified-at-HEAD claim for that file was
wrong. The spec's own instruction — "population-derive the sweep, do not fix the three known sites
and call the class closed" — is what made the discrepancy visible instead of shipping a partially
retired class. This is a direct win for the epic's standing rule that a set-guarding detector must
be population-derived and must publish its population size (409 scanned, 3 offenders).

**2. A defect that two independent read-only reviews called "fails safe" in fact fails OPEN.**
Both phase-2-refine and phase-3-outline recorded a softening correction to R10 — that the collapsed
empty string failed safe to `False` at its one call site. Executing the pre-fix source refuted it:
`_is_marketplace_bundle_module('../marketplace/bundles/foo')` returned `True`, and the embedded
`marketplace/bundles/../../etc/foo` likewise. The helper mis-classified traversal paths as
in-bundle. Two review passes softened a severity by *reasoning about* a call site instead of
*executing* it. Filed as finding `eb608d` and carried separately as a candidate lesson.

## Verification posture, stated honestly

Green: CI across 13 checks including whole-tree `verify` at the merged HEAD; `plugin-doctor` clean
over 31 rules; pre-submission self-review clean over 56 candidates; every regression test verified
red-before-green.

**Not green: the review barrier.** The merge proceeded under an explicit operator authorization
recorded as `merge_authorizations.barrier-ask-override` (`gap_class: review-barrier-gap`, granted
2026-08-09T19:39:45Z at HEAD `cbb184c9d`). It was granted over `participation_complete=false` with
`unproven_bots=[pr-agent, coderabbit, sourcery]` — `pr-agent=participated_stale`,
`coderabbit=refused_awaitable`, `sourcery=refused_hard`. **No reviewer produced an actionable
comment on this diff.** The configured disposition was `fail_into_loopback`, so this was a
deliberate operator departure from standing config, not the configured ask path. The epic should
read this landing as CI-and-local-gates verified, **not** as bot-reviewed.

## Residue the epic should track

Nine findings remain `pending` in the plan's findings store and will not survive the plan
directory. Three are carried separately as `candidate-lesson` / `finding` messages in this same
drain (marked below); the other six are recorded here so none is silently lost.

| Hash | Type | Component | Observation | Carried separately |
|------|------|-----------|-------------|:------------------:|
| `a8d263` | insight | `plan-marshall:automatic-review` | Same bot, same unchanged HEAD, classified `participated` then `stale` by two fetches ~24 min apart | yes |
| `61284d` | insight | `plan-marshall:automatic-review` | Quorum passed on an empty required-bot review while both optional bots refused — third consecutive occurrence | yes |
| `eb608d` | insight | `plan-marshall:manage-architecture` | R10 fails OPEN pre-fix; two read-only reviews softened it by reasoning rather than executing | yes |
| `1d3916` | improvement | `plan-marshall:manage-solution-outline` | `get-module-context` unusable at phase-3 for any `use_worktree=true` plan | yes (as `finding`) |
| `f2543e` | bug | `plan-marshall:workflow-integration-git` | `prune-local-and-remote-ref` errors on the branch `worktree-remove` already deleted, then aborts before the remote-ref prune — stale `origin/` ref survived and needed a manual `git update-ref -d` | no |
| `d0cd33` | improvement | `plan-marshall:build-pyproject` | Whole-tree `module-tests` (642s) exceeds its learned daemon timeout while the superset `verify` completes in 215-537s | no (see 007 + correction 010) |
| `3ae562` | improvement | `plan-marshall:manage-build-server` | Daemon interaction-audit log holds none of this session's ~15 builds, yet reports `count: 17` as a complete answer | no |
| `866492` | improvement | `plan-marshall:phase-6-finalize` | PR intent-section budget truncates the tail, and the tail is the non-goals — the one section whose absence generates false review findings | no |
| `045711` | improvement | `plan-marshall:manage-providers` | `Retry-After` delta-seconds honoured verbatim with no upper clamp; deliberately NOT fixed here (a contract change, and a test pins the current behaviour) | no |

Note that `f2543e`, `3ae562` and `866492` are defects in plan-marshall's own finalize machinery
observed while finalizing, and `866492` sits in `phase-6-finalize` itself.

## Sequencing note for the epic

The spec flagged this plan as task-grouped rather than component-grouped and warned it collides
cheaply across five components. In the event, `manage-providers` (PLAN-TRUTH-011) had already
landed, and the `opencode/emitter.py` overlap with PLAN-TRUTH-071 was carried here rather than
handed off. **PLAN-TRUTH-071's `lstrip` deliverable is therefore already satisfied by this
landing** — check it before re-staging that work.
