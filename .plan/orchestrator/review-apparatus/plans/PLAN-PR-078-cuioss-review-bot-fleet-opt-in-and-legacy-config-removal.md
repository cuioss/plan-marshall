# PLAN-PR-078: cuioss-review-bot fleet opt-in, and removal of the legacy repo-local config

epic: review-apparatus
workstream: WS-02

> Staged plan spec. It is one shippable unit of work, ready for `/plan-marshall` hand-off. The orchestrator
> EMITS the command below; it never launches the plan inline. This spec is SELF-SUFFICIENT: every per-plan
> carry is authored here.
>
> **Not affected by the PM-MCP supersession (2026-09-26).** The whole surface is foreign-repository
> configuration, which PM-MCP does not replace. This is the rollout half `PLAN-PR-066` deliberately left
> per-repository.

## Objective

`PLAN-PR-066` shipped the run-time review charter and the per-repository opt-in
(`cuioss-review-bot: {enabled, packs, additional_rules}` in `.github/project.yml`), and enabled it only in its
pilot, plan-marshall. A 2026-09-28 org sweep found the rest of the fleet in three states:

1. **Legacy.** Three repositories run the reviewer through the pre-066 mechanism: a caller named
   `.github/workflows/pr-agent.yml`, and in two of them a generated repo-local `.pr_agent.toml` carrying the
   **java** pack.
2. **Not enrolled.** Seventeen code repositories have no reviewer caller at all.
3. **Stale reference.** `cuioss/coderabbit` `.coderabbit.yaml` still names the retired
   `reusable-pr-agent-review.yml`.

Bring every repository in scope to ONE shape:
- a `.github/workflows/cuioss-review-bot.yml` caller pinned to the current org release;
- a `cuioss-review-bot:` block in `.github/project.yml` with `enabled: true` and operator-confirmed `packs`;
- no repo-local `.pr_agent.toml`.

⛔ **The `.pr_agent.toml` files are NOT dead config, so they must never be deleted alone.** On the central-charter
path the org workflow sets no `PR_REVIEWER.EXTRA_INSTRUCTIONS`. PR-Agent then merges the repo-local
`.pr_agent.toml` over the central settings (`reusable-cuioss-review-bot.yml` ≈:119), so API-Sheriff's and
TokenSheriff's java pack is what their reviewer applies TODAY. Deleting the file without adding the
`project.yml` opt-in in the same PR silently drops the java pack. A repo-local `.pr_agent.toml` can also
reconfigure `GITHUB_ACTION_CONFIG.PR_ACTIONS` (≈:513), which moves the scope of the empty-review guard
(`PLAN-PR-002`) without anyone noticing. That is a second reason to remove it.

## Population (operator decision 2026-09-29)

Derived by an org sweep of 30 repositories (27 active, 3 archived). Each repo was checked with `ci repo file
read` using its `state` field (NOT `status`, which is `success` even for an absent file), and callers were
confirmed with `ci org search-code` for `reusable-cuioss-review-bot.yml` (26 hits, complete).

| Group | Repositories | Action |
|---|---|---|
| **Migrate** (3) | `API-Sheriff` (`.pr_agent.toml` java, generated), `TokenSheriff` (`.pr_agent.toml` java, generated), `cui-http` (no toml) | Rename the caller `pr-agent.yml` → `cuioss-review-bot.yml`, add the `project.yml` opt-in, remove `.pr_agent.toml` where present. ALL in ONE PR per repo |
| **Enroll** (17) | `cui-core-ui-model`, `cui-java-module-template`, `cui-java-tools`, `cui-jsf-components`, `cui-jsf-test-basic`, `cui-open-rewrite`, `cui-portal-core`, `cui-portal-ui`, `cui-reference-documentation`, `cui-test-generator`, `cui-test-juli-logger`, `cui-test-keycloak-integration`, `cui-test-mockwebserver-junit5`, `cui-test-value-objects`, `nifi-extensions`, `plan-marshall-mcp`, `playwright-test-artifacts` | Add the caller, the `project.yml` opt-in, and the `skip-bot-review` label if it is missing |
| **Excluded by operator** | `.github`, `coderabbit`, `cuioss-review-bot`, `cuioss.github.io`, `cuioss-organization`, `cuioss-parent-pom` | No enrollment. `cuioss-review-bot/.pr_agent.toml` is the CENTRAL settings file every run reads: ⛔ never remove it |
| Already migrated | `plan-marshall` (`enabled: true`, `packs: [python, plugin]`) | none; reference shape |
| Archived | `cui-llm-rules`, `portal-tomcat-runtime`, `portal-vault-sample` | none |

## ⛔ Release safety: a `project.yml` edit must never publish (analysis 2026-09-29, first-party)

Every in-scope repository's `.github/workflows/release.yml` fires on `pull_request: closed` with
`paths: ['.github/project.yml']` and `if: merged == true`. So EVERY PR this plan merges starts a release run. What
stops that run from publishing differs by release path:

| Repositories | Release path (pin) | What stops an accidental publish |
|---|---|---|
| 19 Maven repos (all in scope except `playwright-test-artifacts`) | `reusable-maven-release.yml` @ `79bd910` (v0.34.0) | The `guard` job (`.github/actions/release-guard`, present since v0.18.0 / #224). It proceeds only when `release.current-version` CHANGED on the merge commit versus its first parent AND that version is untagged. Every error (unparseable YAML, unreadable parent, missing `release` block) resolves to "do not release". It was introduced after a Java-version bump published an irrevocable `de.cuioss.sheriff.api:*:1.0.0` on 2026-07-12. |
| `playwright-test-artifacts` | `reusable-npm-publish.yml` @ `79bd910` (v0.34.0) | **NOTHING in the workflow.** It runs `npm version <current-version> --allow-same-version`, then `npm test`, then `npm publish`, unconditionally. Today only npm's refusal to republish stops it: `current-version: 0.1.1`, and npm `latest` = `0.1.1` (read 2026-09-29). So the run fails red and publishes nothing, but only while those two agree. |

**Binding rules for every PR in this plan:**
1. A PR NEVER edits the `release:` block of `project.yml`. The opt-in is additive under a new top-level key.
   D0 re-reads each repository's `release.current-version`; every PR's diff must leave it byte-identical.
2. A malformed `project.yml` fails the guard closed (red, no release), so it is a defect but not a publish.
   Validate each edit against the org schema before merge.
3. D4 additionally reads each post-merge release run and records the guard's `proceed=false` and its
   `reason`. A release run that reached the publish job is a STOP-THE-LINE incident, never a footnote.
4. ⛔ `playwright-test-artifacts`' `project.yml` is not touched before D0b has shipped and its pin is bumped.

## Deliverables

0. **D0b (PREREQUISITE, operator decision 2026-09-29): guard the npm release path.** In `cuioss-organization`,
   wire the existing `release-guard` composite action into `reusable-npm-publish.yml` the same way
   `reusable-maven-release.yml` does:
   - a `guard` job with `fetch-depth: 0` and `fetch-tags: true`;
   - `publish` gated on `needs.guard.outputs.proceed == 'true'`;
   - `workflow_dispatch` still forces a release.

   The guard's already-tagged check covers npm's `v`-prefixed tags: `is_already_tagged` (≈:183) matches bare,
   `v`-prefixed and `${artifactId}-` forms. That was verified 2026-09-29 and is to be re-checked at HEAD, and
   a test must pin it for the npm tag scheme. Add tests
   mirroring the Maven guard's, release a new org version, and bump `playwright-test-artifacts`' release
   pin. Only then may D2 edit its `project.yml`. This closes the gap for every future `project.yml` edit in
   an npm repository, not only this rollout's.
1. **D0 (GATE, mutates nothing): derive and confirm the pack table.**
   - Re-run the population sweep at HEAD, using `state`, not `status`, and HALT on any drift from the table
     above.
   - For every repository in Migrate + Enroll, derive candidate `packs` from the repository's languages and
     build files. The published packs are `docs`, `java`, `javascript`, `oci`, `plugin`, `python` and `reqs`
     in `cuioss/cuioss-review-bot` `packs/`; the spine is unconditional and never listed. The existing
     `java` pack is the minimum for API-Sheriff and TokenSheriff.
   - Present the per-repo table to the operator (`AskUserQuestion`) and write nothing before it is confirmed.
   - Record the confirmed table in the plan.
2. **D1: migrate the three legacy repositories.** One PR per repository, per the Migrate row. Copy the caller
   from `cuioss-organization` `docs/workflow-examples/cuioss-review-bot-caller.yml` at its current pin (the
   release current at run time, not a hard-coded SHA from this spec). In API-Sheriff and TokenSheriff the
   `.pr_agent.toml` removal and the `packs` addition are atomic.
3. **D2: enroll the seventeen repositories.** One PR per repository: the caller, the `project.yml` block with
   the D0-confirmed packs, and the `skip-bot-review` label (the caller's documented prerequisite). A repository
   whose `project.yml` fails the org schema is reported, never force-written.
4. **D3: fix the stale reference.** In `cuioss/coderabbit` `.coderabbit.yaml`, change the comment naming
   `cuioss-organization`'s `reusable-pr-agent-review.yml` `changes` job to the current
   `reusable-cuioss-review-bot.yml`.
5. **D4: verify the rollout live, per repository, not by merge alone.** After each PR merges, the next real PR
   in that repository (or a dedicated no-op PR) must show:
   - the "Assembled review charter (spine; packs: …)" log line naming the confirmed packs;
   - `review / changes` and `review / review` behaving as `PLAN-PR-002` specified.

   A repository where no run could be observed is reported as `unverified`, never as done.
6. **D5: the final report.** Every repository in the population with its end state:
   - caller present and name;
   - `.pr_agent.toml` absent;
   - opt-in `enabled`;
   - packs;
   - live-verified, or unverified with the reason.

   The report states the population it was computed over. Transmitted as this plan's landing.

## Claim Labels

- OBSERVED (2026-09-28, first-party via `ci repo file read` + `ci org search-code`): only plan-marshall,
  API-Sheriff, TokenSheriff and cui-http call `reusable-cuioss-review-bot.yml`. The latter three still name the
  caller `pr-agent.yml`. API-Sheriff and TokenSheriff carry a generated java `.pr_agent.toml`. No active
  repository except plan-marshall has a `cuioss-review-bot:` block, and none has a legacy `pr-agent:` block.
  Confirm/refute by re-running D0's sweep.
- OBSERVED (2026-09-28, `cuioss-organization` `origin/main`): the central-charter path does not set
  `PR_REVIEWER.EXTRA_INSTRUCTIONS`, so a repo-local `.pr_agent.toml` is merged and its pack is live. A
  repo-local file can override `PR_ACTIONS`. Confirm/refute at `reusable-cuioss-review-bot.yml` ≈:119, ≈:396–413
  and ≈:513.
- ⚠ CORRECTION recorded: an earlier sweep in the orchestrator session read `status: success` as "file
  present" and wrongly reported the caller in all 27 repositories. `status` reports the READ, and `state`
  reports the FILE. D0 must use `state`.
- HYPOTHESIS: the "22/22 consumer pin-bump PRs" in `PLAN-PR-002`'s landing bumped OTHER org workflows, not a
  reviewer caller, since 23 active repositories have none. Not load-bearing here.

## Expected Surface

- OBSERVED: `API-Sheriff` → `.github/workflows/pr-agent.yml`
- OBSERVED: `API-Sheriff` → `.github/workflows/cuioss-review-bot.yml`
- OBSERVED: `API-Sheriff` → `.pr_agent.toml`
- OBSERVED: `API-Sheriff` → `.github/project.yml`
- OBSERVED: `TokenSheriff` → `.github/workflows/pr-agent.yml`
- OBSERVED: `TokenSheriff` → `.github/workflows/cuioss-review-bot.yml`
- OBSERVED: `TokenSheriff` → `.pr_agent.toml`
- OBSERVED: `TokenSheriff` → `.github/project.yml`
- OBSERVED: `cui-http` → `.github/workflows/pr-agent.yml`
- OBSERVED: `cui-http` → `.github/workflows/cuioss-review-bot.yml`
- OBSERVED: `cui-http` → `.github/project.yml`
- OBSERVED: each of the 17 Enroll repositories → `.github/workflows/cuioss-review-bot.yml`
- OBSERVED: each of the 17 Enroll repositories → `.github/project.yml`
- OBSERVED: `coderabbit` → `.coderabbit.yaml`
- OBSERVED (D0b): `cuioss-organization` → `.github/workflows/reusable-npm-publish.yml`
- OBSERVED (D0b): `cuioss-organization` → `.github/actions/release-guard/`
- OBSERVED (D0b): `cuioss-organization` → `test/`
- OBSERVED (D0b): `playwright-test-artifacts` → `.github/workflows/release.yml`
- OBSERVED (absence): NO file inside `plan-marshall` is touched. plan-marshall is the reference shape.

## Dependencies and Sequencing

- Depends on: `PLAN-PR-066` (shipped) and `PLAN-PR-002` (shipped: the `changes` pre-job D4 verifies).
  Overlaps with nothing live; every other row of this epic is terminal.
- ⚠ **Setup precondition:** local checkouts are not guaranteed for every repository. The plan obtains each
  checkout, or works through the CI abstraction's `--project-dir`, before editing. `gh` is never called
  directly.
- ⚠ **Quota load:** enrolling 17 repositories adds review-bot (Vertex/Gemini) runs on every new PR org-wide.
  Order D1 before D2 so the three already-reviewed repositories are fixed first. Enrollment may be staged in
  batches if a live run shows the quota under pressure.
- ⛔ **Sequencing (release safety):** D0b ships and is released before any PR touches
  `playwright-test-artifacts/.github/project.yml`. The Maven repos may proceed in parallel with D0b, because they
  are already guarded.
- ⛔ **Prohibited:** editing any `release:` block; in any PR that does not also add the opt-in carrying at least
  its pack; touching `cuioss-review-bot/.pr_agent.toml`; hard-coding a workflow SHA from this spec.
- Residual R1 (`PLAN-PR-002`) is untouched: this plan does not enable `synchronize` / `handle_push_trigger`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-078-cuioss-review-bot-fleet-opt-in-and-legacy-config-removal.md"
```

## Write-Boundary

The plan implementing this spec writes only to the foreign repositories named above. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message, reports its outcome through
its PRs and that message, and uses the sole sanctioned inbox write mechanism.
