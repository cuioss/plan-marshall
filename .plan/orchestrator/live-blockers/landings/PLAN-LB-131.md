# Landing Analysis: PLAN-LB-131 — the foreign gate never takes the default branch as the change's branch, and a cleaned-up merged branch still reads merged

epic: live-blockers
workstream: WS-01
pr: #1948 (merge commit `652d977cf48024e28b1ac3e0014c2d061a0ec5ec`, one parent `d1e4b5128`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Corroborated against git: the merge is a merge-queue squash with one parent (`d1e4b5128`, the PLAN-LB-129 merge), fourteen files, +720/-74. The facts block (`pr=#1948`, `merge_state=merged`, `deliverables 3/3`) agrees with git. `total_tokens=unknown` is an unobserved fact, not a defect. `self-review:budget-exhausted` is a lane state, not a `clear`: the lane stopped after three rounds with five new LOW items open, and the operator chose to record them as residue.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the default branch is never a change's branch; a declaration wins | shipped-as-specified | `_default_branch` reader (`foreign_pr_gate.py:196-230`, re-read) with a 60 s bound; `_branch_for_repo` (`:296-351`, re-read): declared X with a checkout on the default returns X (326-327), undeclared with a checkout on the default is `branch_is_default` (340-345), an unreadable default with no declaration is `default_branch_unreadable` (333-339). Tests (leaf): `test_foreign_pr_gate_gate.py` 588, 618, 633. |
| D2 — a declared branch whose local ref is gone is read from the remote, then its merged PR | shipped-as-specified | `_branch_tip_sha` (`_github_pr.py:1567-1580`, re-read): `refs/heads/X`, `refs/remotes/origin/X`, then `ls-remote --heads origin X` compared for exact ref equality; absent everywhere gives `(None, None)` and the PR listing classifies (1708-1742, re-read): OPEN is an error, MERGED reads `merged` with `tip_sha: null`, none is `branch_absent`. The GitLab hypothesis is refuted (no landing-state handler exists there; leaf, pickaxe). |
| D3 — the documents state the rule once, in present tense | shipped-as-specified | `archive-plan.md:37`, the module docstring, `_cmd_lifecycle.py:877-879` and two test docstrings (leaf, not re-read); the doc test `test_foreign_pr_gate_docs.py` (leaf). |

**The lane's claim "no surface drift: every touched path is in the spec's Expected Surface" is false.** The re-read path list (`git diff --name-only`) shows four files outside it: `manage-solution-outline/templates/deliverable-template.md`, `tools-integration-ci/SKILL.md`, `tools-integration-ci/standards/api-contract.md` and the new `test_foreign_pr_gate_docs.py`. The leaf traced each to a deliverable: the template drops a sentence `archive-plan.md` removed, the two contract documents state the new `tip_sha: null` shape under the current-state rule, and the doc test is D3's Done-when with no file named. So none is unexplained, but the claim is an overclaim in the report, and the gap is partly the spec's (D2 changes a response contract and its surface omits the contract documents).

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, `orchestrator.analyze` surface), and the orchestrator re-read the points marked as re-read. The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for, and this landing's read must not share context with the three sibling landings drained in the same session.
- **Verdict:** layer 1 findings (1, minor); layer 2 findings (2, minor); layer 3 findings (7, minor). No blocker or major.

Re-read at `foreign_pr_gate.py` 196-230 and 296-353, `_github_pr.py` 1555-1580 and 1700-1755, and the changed path list. **Not re-read** (unverified leads): the test lines the leaf cites (`test_foreign_pr_gate_gate.py` 390-645, `test_pr_landing_state_*`), `archive-plan.md`, `deliverable-template.md:69`, `tools-integration-ci/SKILL.md:337`, `api-contract.md:150,165`, the pickaxe for the GitLab handler, the claim that `ci org list-repos` reports a default branch, and the git facts the stale-`origin/HEAD` finding rests on.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | D2's premise "absent everywhere means nothing unlanded exists under that name" is true of the NAME only. The only link between the plan and the PR history in that arm is the declared name, and the verify-first reasoning recorded in the code covers a reused name but not a mis-declared one. | checked (code re-read) | refutes | `_github_pr.py:1708-1718` |
| — | D1 states the default branch is never a change's branch for the CHECKOUT only; it is silent on a DECLARATION equal to the default, and the code inherits the gap (L3-3). | checked (re-read) | confirms | `foreign_pr_gate.py:319-332` |
| — | The spec's D2 Expected Surface omits the contract documents its response-shape change forces. | checked (leaf) | confirms | `api-contract.md:150` |

**Layer 1 verdict:** findings — 1 (minor)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `foreign_pr_gate.py:196-351` | `test_foreign_pr_gate_gate.py` 588/618/633 (leaf) | none | checked |
| D2 | `_github_pr.py:1567-1580, 1708-1742` | `test_pr_landing_state_states.py` 258/276/293/306 and `_errors.py:164` (leaf) | none | checked |
| D3 | `archive-plan.md:37`, docstring, `_cmd_lifecycle.py:877-879` | `test_foreign_pr_gate_docs.py` 56/69/85 (leaf) | the new doc-test file | checked |

- **L2-1 (minor):** the report's "no surface drift" claim is false for four files, each explained by a deliverable (see above).
- **L2-2 (minor):** the report's hypothesis "the CI abstraction has NO default-branch verb" is partly refuted: `ci org list-repos` emits `default_branch` per repository (leaf, not re-read), org-wide and GitHub-only, so there is no single-repository verb. The lane's own residue item O4 already says so. And "`ls-remote --symref` works without credentials" is not shown by reading; for a private HTTPS remote it needs credentials.
- Also inaccurate, minor wording: the report says the default is read "only for a repository with an undeclared branch"; it is also read for a declared branch whose checkout differs (`foreign_pr_gate.py:325`, re-read).

Confirmed against the lane's claims: the plan-id-fallback test is gone, the disagreement test uses checkout `fix/other`, and the three must-hold cases exist (leaf, not re-read). The lane's five LOW residue items O1, O2, O3a-d and O5 are all borne out by the diff (O1 at `_github_pr.py:1723-1724`, re-read; O2 at 1556-1558, re-read). Whether the tests ran green, their mutation evidence and their test-first order are not shown by reading.

**Layer 2 verdict:** findings — 2 (minor)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `_github_pr.py:1727-1738` | `foreign_branch` declares a stale or wrong name X whose old same-repository PR merged and whose refs are gone everywhere; the real change was pushed on Y with no PR; the checkout is back on the default branch (a declaration wins, `foreign_pr_gate.py:326`) or detached | `landing-state` reads `merged` from the name alone and the gate clears an unlanded change. Before this landing the tip was unresolvable and the read was an error. Needs a mis-declaration; the same trust already applied while a stale name's refs still existed | minor |
| L3-2 | `_github_pr.py:1567-1572` | name X reused; local `refs/heads/X` stale at the head of an old merged PR; new commits pushed to X from another clone with no PR | local-first order makes the old tip match the merged PR and read `merged`, so the gate clears. The reverse (local behind a merged head updated remotely) gives a wrong `pushed_no_pr` block. Edge case; the old `rev-parse X` also preferred the local ref | minor |
| L3-3 | `foreign_pr_gate.py:319-332` | `foreign_branch: main` declared, checkout `main` or detached | a declaration equal to the default branch is accepted; `landing-state` on `main` answers `pushed_no_pr` and the gate blocks for good with an "open a PR" message instead of a `branch_is_default` refusal. Fails closed, misleading text | minor |
| L3-4 | `foreign_pr_gate.py:213-219` | the remote default is renamed after clone (`master` to `main`) | `refs/remotes/origin/HEAD` is set at clone time and not updated by fetch (a git fact the leaf states; not re-read), so the default reads the old name: an undeclared checkout on `main` is taken as a change branch and blocks wrongly. A local branch named `origin/main` makes `--short` print `remotes/origin/main` and the strip misses it. Fails closed | minor |
| L3-5 | `test_foreign_pr_gate_docs.py:40-66` | a second, reworded or lower-case statement of the rule | the exactly-once test counts one case-sensitive phrase and the obsolete-wording test bans two literals, so a restatement passes (leaf, not re-read) | minor |
| L3-6 | `test_pr_landing_state_errors.py:142-150`, `test_foreign_pr_gate_gate.py:479-483` | — | the unreadable-remote test asserts only that `branch_absent` is absent, and the timeout test does not pin the 60 s bound (O3b and O3d; leaf, not re-read). No test covers a declaration equal to the default, or a declared branch with the checkout on an unreadable default | minor |
| L3-7 | `_github_pr.py:1723-1725, 1556-1558` | — | the OPEN-arm message says the branch exists in "no PR head, yet an OPEN PR names it as its head" (self-contradictory), `branch_missing_but_pr_open` is passed as error context and not as a code, and the `_branch_tip_sha` docstring misdescribes when the remote arms help (O1, O2; re-read) | minor |

**Layer 3 not shown by reading:**

- Whether `gh` always emits `isCrossRepository` (a missing field is counted as same-repository, `_github_pr.py:1703`, re-read, fail-open only if `gh` omits a requested field); and whether `ls-remote` can stall on a credential prompt, since `GIT_TERMINAL_PROMPT=0` is set nowhere (fails closed at the 60 s bound).
- A tip from the `ls-remote` arm may not be a local object, so `git branch -r --contains <sha>` errors rather than answering `pushed_no_pr`. Reachable when X was pushed from another clone and never fetched; the lane called it unreachable. Fails closed.
- Pre-existing and outside this landing: only `pushed_no_pr` blocks, so an `unpushed` read (a commit on no remote) is a repository row and the gate CLEARS. By design per `archive-plan.md:35`, but a clear for a change that is not landed.

**Layer 3 verdict:** findings — 7 (minor); not shown by reading — 3

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec standing | the gate fails closed; no fallback to `feature/{plan_id}` | conforms | `foreign_pr_gate.py:333-339`; the name-only `merged` arm at `_github_pr.py:1727` is the one trusting exception (L3-1) |
| spec standing | a fixture answer is one the real verb can give | deviates | the `gh` fixtures omit `isCrossRepository` although the handler requests it (leaf: `test_pr_landing_state_states.py` 216-238); the gate fixtures are realistic |
| spec standing | executor regeneration only if a verb or flag is added | conforms | no verb or flag added; the resolver is a Python keyword argument |
| spec standing | out of scope by ruling 20 | conforms | the diff touches none of those surfaces |
| spec Expected Surface | touched paths within the surface | deviates | four files outside it, each forced by a deliverable (L2-1) |
| spec standing | tests use the `PLAN_MARSHALL_HOME` fixture | not_shown_by_reading | conftest not read |
| CLAUDE.md § Documentation Standards | current state only, no version history | conforms | `archive-plan.md:37`, the docstring and `_cmd_lifecycle.py:877-879` are present tense (leaf) |
| CLAUDE.md / code rules | subprocess as argv list, bounded | conforms | `foreign_pr_gate.py:207-211` (re-read) |

## Metrics and Anomalies

- Tokens: `unknown`; out of scope. `landing-check` `missing_keys: [total_tokens]` is no defect.
- Anomalies: the build gate failed four times on `/tmp` inode exhaustion (`OSError: [Errno 28]`, 0 to 4.5k free inodes of 1048576) in modules this plan does not touch, and the lane asked the operator four questions about it (reclaim `/tmp`, retry, open the PR on CI evidence, record the round-3 items). This is the leak PLAN-LB-141 has since closed in the test harnesses. 22 routed builds, all `daemon_longpoll`; most of the wall clock was queue time behind other sessions' jobs. One guard refusal (R5, an accidental malformed invocation, not retried). Self-review ended `budget-exhausted` with the five LOW items recorded as residue.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed `5b12a384f`; refused on the two later heads; the standing review authorization applied on the merge head. Four findings: inline-1 declined (the spec fixes the local-then-remote order; the lane says a stale local ref blocks, "never clears" — overstated, see L3-2), inline-2 and both nitpicks fixed in `e2b91a044`. Sourcery (optional) refused on quota. Review numbers re-read with `runbook_lane review-gate --pr-number 1948`: `unresolved_review_threads` 0 (agrees) and `review_body_findings_total` 4 (agrees); `review_body_findings_handled` is **not re-verified** (no progress file was passed).
- CI/merge: merge queue (merge_group run success, per the lane, not re-read); squash with one parent.
- Sonar: `n/a`.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-131 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-131 --field pr --value 1948`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-131 --field landing --value landings/PLAN-LB-131.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-131 --field plan_marshall_plan_id --value rb-lb-131-foreign-gate-default-branch`
- [x] epic.md narrative reconciled against the queue rows
- [x] defect/watch opened or retired
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

(Each box is ticked only after the call it names has returned.)

## Follow-Ups

- No fix plan: no blocker and no major. The PLAN-LB-126 HIGH Open Defect (the foreign gate blocks a merged change when the tree sits on the default branch) is retired by this landing.
- **Watch:** L3-1 to L3-7 and the three points not shown by reading.
- **Sequencing:** PLAN-LB-133 (`_cmd_lifecycle.py`) was held back for this plan; it is now admissible.
