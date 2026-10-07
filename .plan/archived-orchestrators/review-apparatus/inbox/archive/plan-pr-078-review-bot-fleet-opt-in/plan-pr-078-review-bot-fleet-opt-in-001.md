envelope_version=1
sender_type=plan
sender_id=plan-pr-078-review-bot-fleet-opt-in
epic=review-apparatus
kind=landing
created=2026-10-06T17:57:39Z

## What landed

plan-pr-078-review-bot-fleet-opt-in (PLAN-PR-078) fleet report: 7 of 20 in-scope repositories carry the cuioss-review-bot opt-in on their default branch, 13 are deferred unwritten on an org schema failure, and 1 of the 7 is live-verified.

This message is the fleet report (spec deliverable D5), written at the end of the execute phase. The host plan's own pull request, merge state, token total and finalize step outcomes do not exist yet at this point, so those keys below are recorded as gaps (`unknown`), not as settled values.

```landing-facts
schema=landing-facts/1
plan_id=plan-pr-078-review-bot-fleet-opt-in
epic=review-apparatus
pr=unknown
merge_state=unknown
cleanup_owed=unknown
deliverables_total=10
deliverables_done=8
total_tokens=unknown
steps=unknown
```

## Residue

### Population

- Computed over the spec's 30-repository table. The org held 31 repositories at sweep time; `plan-marshall-telemetry` (private, unclassified) was excluded by operator decision and is not part of any count below.
- The 20 in-scope rows (3 Migrate + 17 Enroll) are reported in full. The other 10 rows were NOT re-read by this report: 6 excluded by operator (`.github`, `coderabbit`, `cuioss-review-bot`, `cuioss.github.io`, `cuioss-organization`, `cuioss-parent-pom`), 1 already migrated (`plan-marshall`), 3 archived (`cui-llm-rules`, `portal-tomcat-runtime`, `portal-vault-sample`).
- `deliverables_done=8` of 10: deliverables 5 and 6 (the two enrollment batches) closed at reduced scope by operator decision — 3 of their 16 repositories were enrolled, 13 were not.

### How each column was read

- Caller, `.pr_agent.toml`, opt-in and packs: `ci repo file read --repo cuioss/{repo} --path ...` on the default branch, judged on the `state` field (`found` / `not_found`), never on `status`. All 20 repositories were read for `.github/project.yml`, `.github/workflows/cuioss-review-bot.yml` and `.pr_agent.toml` (60 reads, one observation each, taken 2026-10-06 around 17:50Z).
- Legacy caller `.github/workflows/pr-agent.yml`: read for the 3 Migrate repositories only (`not_found` in all three). For the 17 Enroll repositories its absence rests on the earlier caller census, not on a read in this report.
- Live verification: the first pull request numbered after the plan's own merged pull request in that repository (`ci pr list --state all`), its reviewer run from `ci checks status`, then `ci checks logs --run-id {id} --scope full --match "Assembled review charter"`. `pr view` / `pr list` carry no created or merged timestamps, so "created after the merge" rests on pull-request number order. Observed once; nothing was waited for; no probe pull request and no `/review` comment was issued.
- Pre-merge release-guard class: read at merge time during deliverables 4-7 (default-branch `release.yml` plus the pinned reusable workflow).
- Post-merge release run: job conclusions from `ci checks status` at merge time. The guard job's literal `proceed` / `reason` values were looked for with `checks logs --scope full --job "release / guard" --match "proceed="` on five runs and returned `match_count: 0` on each; the playwright run carries only the line `Set output 'proceed'` without a value. So `proceed=false` is inferred from guard SUCCESS + release/publish SKIPPED, not read literally.

### The 7 repositories carrying the opt-in

Every one: caller `.github/workflows/cuioss-review-bot.yml` found (blob `de189704`, pinned `reusable-cuioss-review-bot.yml@b2de4107 # v0.36.0`), `.pr_agent.toml` not_found, `cuioss-review-bot: enabled: true` with `additional_rules: []`.

| Repository | Group | PR (merge commit) | Packs on default branch | Live verification | Pre-merge guard class | Post-merge release run |
|---|---|---|---|---|---|---|
| API-Sheriff | Migrate | #399 (278e5d34) | java, javascript, oci | unverified — on the first later PR #400 (reviewer run 37492467999) both `review / changes` and `review / review` were SKIPPED; charter read returned match_count 0. PR #401 is open and was not read (the rule keeps the first PR) | guarded | run 37476407779: release/guard SUCCESS; release, wait-for-maven-central, propagate-to-consumers, Publish image to GHCR all SKIPPED |
| TokenSheriff | Migrate | #782 (21f56fe7) | java, javascript | unverified — no pull request exists after #782 | guarded | run 37480009892: release/guard SUCCESS; release, wait-for-maven-central, propagate-to-consumers SKIPPED |
| cui-http | Migrate | #273 (74739adf) | java | unverified — reviewer run not locatable through the CI abstraction: `checks status` for the first later PR #274 lists 27 checks, none from the reviewer workflow. This is not evidence the reviewer did not run | guarded | run 37480682022: release/guard SUCCESS; release, wait-for-maven-central, propagate-to-consumers SKIPPED |
| cui-java-module-template | Enroll | #156 (b6d98fc7) | java | unverified — no pull request exists after #156 | guarded | run 37490191298: the caller job `release` was SKIPPED as a whole (its `release.yml` gates on the repository not being the template), so the guard job was never reached; guard outcome not observed for this repository; no publish job ran |
| cui-open-rewrite | Enroll | #190 (630d7920) | java | unverified — no pull request exists after #190 | guarded | run 37490557569: release/guard SUCCESS; release, wait-for-maven-central, propagate-to-consumers SKIPPED |
| plan-marshall-mcp | Enroll | #33 (2c8f776d) | java | LIVE-VERIFIED on PR #34, reviewer run 37504777427: charter line `Assembled review charter (spine; packs: java; additional rules: 0)` names exactly the confirmed pack; `review / changes` SUCCESS, `review / review` SUCCESS | no-release-path (no `release.yml` on the default branch; supersedes the pack table's `guarded` cell) | none — no release workflow exists, so no release run could start (derived from the absent file; no run list was read) |
| playwright-test-artifacts | Enroll | #185 (5de59d8d) | javascript | unverified — no pull request exists after #185 | guarded (after the org npm guard, cuioss-organization #307 / v0.36.0, and pin bump #183) | run 37499859390: release/guard SUCCESS; release/publish SKIPPED (no npm publish) |

No repository was halted by the pre-merge release-guard gate; none was classified unguarded at merge time.

`release.current-version` on the default branch: unchanged by this plan in all 7. API-Sheriff now reads `0.2.4` (it read `0.2.3` after #399 merged) — moved by that repository's own release pull request #396 "declare version 0.2.4", not by this plan.

### The 13 deferred repositories (not written, not enrolled)

Every one, read on the default branch: caller `cuioss-review-bot.yml` not_found, `.pr_agent.toml` not_found, no `cuioss-review-bot:` block in `project.yml`. Live verification: unverified — not enrolled, so there is no reviewer run to observe. No pre-merge guard gate and no release run apply, because no pull request was opened. Their pre-existing `project.yml` fails the org schema whole-file on keys this rollout does not touch; the spec binds "reported, never force-written". Follow-up: lesson `2026-10-06-15-001` (fix the schema drift at the source, then enroll these 13 with the confirmed packs).

| Repository | Confirmed packs (not applied) | Schema cause |
|---|---|---|
| cui-core-ui-model | java | `github-automation.auto-merge-build-timeout` is not a schema property |
| cui-jsf-components | java, javascript | `auto-merge-build-timeout` |
| cui-portal-ui | java | `auto-merge-build-timeout` |
| cui-java-tools | java | two-part `release.next-version` (`2.7-SNAPSHOT`) |
| cui-jsf-test-basic | java | both (`4.4-SNAPSHOT`, `auto-merge-build-timeout`) |
| cui-portal-core | java | both (`1.5-SNAPSHOT`, `auto-merge-build-timeout`) |
| cui-reference-documentation | java, docs | `auto-merge-build-timeout` |
| cui-test-keycloak-integration | java | `auto-merge-build-timeout` |
| nifi-extensions | java, javascript | `auto-merge-build-timeout` |
| cui-test-generator | java | two-part `release.next-version` (`3.1-SNAPSHOT`) |
| cui-test-juli-logger | java | two-part `release.next-version` (`2.2-SNAPSHOT`) |
| cui-test-mockwebserver-junit5 | java | both (`current-version: 1.6`, `next-version: 1.7-SNAPSHOT`, `auto-merge-build-timeout`) |
| cui-test-value-objects | java | both (`2.1-SNAPSHOT`, `auto-merge-build-timeout`) |

The schema verdicts were read by hand against `cuioss-organization` `schema.json`; no validator could run locally (the org charter reader needs PyYAML under the system python3).

### Unverified repositories, listed explicitly

19 of 20 are not live-verified:

- reviewer jobs skipped on the first later PR: API-Sheriff
- reviewer run not locatable through the CI abstraction: cui-http
- no pull request opened since the merge: TokenSheriff, cui-java-module-template, cui-open-rewrite, playwright-test-artifacts
- not enrolled (deferred on schema): cui-core-ui-model, cui-jsf-components, cui-portal-ui, cui-java-tools, cui-jsf-test-basic, cui-portal-core, cui-reference-documentation, cui-test-keycloak-integration, nifi-extensions, cui-test-generator, cui-test-juli-logger, cui-test-mockwebserver-junit5, cui-test-value-objects

### Other items the epic should track

- The three Migrate repositories (API-Sheriff, TokenSheriff, cui-http) were merged on a schema check that covered only the added block. Their `project.yml` carries the same pre-existing whole-file failures (`auto-merge-build-timeout` in all three; two-part versions in cui-http). They need the whole-file re-validation named in lesson `2026-10-06-15-001`.
- The spec's success criterion "every in-scope repository carries `enabled: true` with the confirmed packs" is met for 7 of 20, not 20.
- Why both reviewer jobs were skipped on API-Sheriff #400 was not established.
- `cuioss/coderabbit` #6 (stale reusable-workflow reference) merged as bf1042a4; its v0.36.0 pin-bump pull-request state was never established (the listing errored for that checkout).
- The host plan adds `ci checks logs --scope full --match --job` (successful-run log read) to plan-marshall; that change is committed on the plan branch (5d0d58479) and ships with the plan's own pull request.
- The plan's finalize phase also emits a landing for this run; that later message carries the pull request, merge state, token total and step outcomes left as gaps here.
