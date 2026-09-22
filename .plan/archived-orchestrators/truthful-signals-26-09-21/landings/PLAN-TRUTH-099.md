# Landing analysis — PLAN-TRUTH-099

**Plan:** `the-ledger-has-no-safe-single-row-append`
**Spec:** `plans/PLAN-TRUTH-099-the-ledger-has-no-safe-single-row-append.md`
**PR:** #1434 · **Merge commit:** `3ca7e2c8f` · **Workstream:** WS-01

## Merge corroboration — and the PR id came from PR STATE, not the message

| Source | Result |
|---|---|
| `git log main` | `3ca7e2c8f feat(plan-orchestrator): add queue --add-row single-row append verb (#1434)` |
| `ci pr view --pr-number 1434` | `state: merged`, `merge_commit_sha: 3ca7e2c8f8a1eb0d86e681f34b1933aed164106b` |
| `manage-status list` | absent from the live store |

⚠ **This landing had TWO PR ids** — `#1424` was closed unmerged and replaced by `#1434`. The stamp was
taken from **PR state**, which is the standing rule precisely because a landing message can name a PR
that never merged. ⭐ Here the message and the state agree; the rule was applied anyway.

## ⭐⭐⭐ The verb retires a workaround this orchestrator used FOUR TIMES in this session

`queue --add-row` is live and confirmed on the argparse surface (`--add-row PLAN-NN`, `--slug-value`,
`--workstream`, optional `--status` defaulting to `staged`).

⛔ **Until this landed, every spec this epic staged went in through a whole-array
`manage-status update-field --field plans` rewrite** — 145+ rows re-serialized through one shell
argument with no rollback. This session used that path for `-138`, `-139` and `-140`, each time behind
hand-written key-order / duplicate-id / count assertions **because the mechanism offered none.**

⇒ **The assertions were the workaround, and they are now retired.** Every future append uses the verb.

⭐⭐ **And D1's design choice is the right one for this ledger**: the duplicate-id check is evaluated
**against the fresh in-lock queue rather than a pre-lock snapshot**, so it cannot be defeated by the
read-modify-write race the whole-array path was exposed to.

## ⛔⛔ A defect shipped into the branch and the self-review caught it — and it defeated the plan's own guard

`pre-submission-self-review` found that the `--add-row` id regex anchored with `$`, **which in Python
also matches before a trailing newline.** So `PLAN-07\\n` passed validation, the newline rode into
`row['id']`, and **the exact-string duplicate check never collided.**

⇒ ⛔⛔ **The `duplicate_plan_id` guard this plan exists to add was evadable by ONE TRAILING BYTE.**
Fixed to `\\Z` with two regression tests that fail against the old anchor.

⭐⭐⭐ **This is the counter-example to this epic's own running complaint about that gate.** Two landings
ago the same step matched 0 of 75 candidates in classes it declares. **Here it caught a validator
bypass in the plan's headline deliverable.** ⇒ **The gate is not uniformly blind — it is
inconsistently effective, which is a different and harder problem than being broken.** Record it as a
positive control against the `-108` fold, not as a contradiction of it.

## ⛔ The review loop caught defects in its own repairs — 4 of 6 findings were second-order

*"`1f08b2` re-introduced, ONE LEVEL ABOVE, the exact absent-vs-present state-fold that `b339df`'s fix
removed one level below."*

⇒ **The self-seeding archetype again, and this time inside a REVIEW cycle rather than a self-review
cycle.** This epic's record now carries it at four seams: `-055`, `-075` (four times in one guard),
`-089` (27% of 51 findings), a foreign Java repo, and now a CodeRabbit round. ⭐ **A fix that relocates
a defect one level up is indistinguishable from a fix at the level it was reported.**

## ⚠ The #1424 → #1434 replacement, and a volunteered correction

**Six `@coderabbitai` triggers over ~12 hours and five 90-minute waits produced no review; every trigger
re-armed the window.** Close-and-recreate obtained a full review in **under 15 minutes**.

⭐⭐ **The run then corrected its own explanation.** It had attributed the stall to a free-OSS vs Team
plan difference; the review retrospective checked the persisted envelopes and found **all three, on both
PRs, record `Plan: Team` with the same `0 remain` footer.** ⇒ **The remedy worked and the mechanism was
unfounded — and the run said so unprompted.**

⛔ **That correction is the durable part.** A working remedy with a wrong explanation is how a folk
theory enters a corpus; filing `-014` (*do not infer a plan-tier cause for a stall — read the persisted
envelopes*) is what stops it.

## ⛔⛔ The landing message carries NO facts block — and this is a REGRESSION, not a first

`landing-check`: **`complete: false`, and `missing_keys` is the WHOLE required set of 8.**

| Plan | Landing facts |
|---|---|
| `-126` | none |
| `-093` | facts written OUTSIDE the map |
| `-089` | **complete** |
| `-128` | **complete** |
| **`-099`** | **none again** |

⇒ ⛔ **Compliance is INTERMITTENT, not improving.** Two complete landings in a row did not establish a
trend. ⚠ **And the information is not lost — the message states the PR, the merge sha, the plan id and
the verify result in PROSE.** The producer had every fact and emitted none of them machine-readably,
which is `PLAN-TRUTH-106`'s subject exactly: **a producer that cannot fail its own contract.**

## Reconciliation actions

- Queue: `PLAN-TRUTH-099` → `shipped`; `pr` = `1434`; `landing` = `landings/PLAN-TRUTH-099.md`.
- Inbox: 24 messages drained (18 from this plan, 5 from `lessons-handling`, 1 from `review-apparatus`).
- Capacity: R 2 → 1 of N=3. **Two slots free.**

## Open items this landing leaves

| Item | Owner |
|---|---|
| the `issue_comment` path never verifies a body-published SHA ⇒ every such re-review declines | forwarded → `review-apparatus` |
| the CodeRabbit trigger/rate-limit cluster (a trigger RE-ARMS the window) | forwarded → `review-apparatus` |
| the four context-load columns are absent because the CALLER omits them | forwarded → `code-intelligence-substrate` |
| `emit-landing` compliance is intermittent — fifth data point, first regression | Open Defect; `-106` owns the producer half |
| six retrospective/metrics/executor items | folded to `-104` `-105` `-107` `-117` `-122` `-129` |
| the footprint gates the lessons-consult population | `-136` (third consequence) |

## Metrics

**3h54m / 5.2M tokens / 138M billing-weighted**, 22/22 finalize steps, `ci-verify` ×3 firings,
`automatic-review` ×3 firings.

⭐ **The shortest wall-clock of any landing this epic has drained** — and still 5.2M tokens for a
4-deliverable plan. ⚠ The re-fire counts are disclosed per step (×3, ×3) rather than hidden behind a
`22/22` headline, which is an improvement on the four landings before it.
