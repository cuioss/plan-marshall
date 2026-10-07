envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=review-apparatus
kind=finding
created=2026-08-26T21:13:47Z

# Self-review loop mechanics: termination, coverage, and the fix diff

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule — the PR/review test wins outright, and `pre-submission-self-review`
is your surface.

**Cluster:** 6 lessons. **Suggested fold target:** `PLAN-PR-018` held self-review
completeness at the last drain. Yours to decide.

## The failure mode

The self-review loop's termination predicate, its candidate coverage, and its finding
persistence each bound what it can find — and each bound is invisible from its output.

## The six instances

| Lesson | Instance |
|--------|----------|
| `2026-08-25-15-001` | ⭐ **The loop terminates on "this round found nothing new", which cannot distinguish convergence from oscillation.** A self-seeding loop never produces an empty round — every round's fix authors the next round's finding — so the predicate can only ever terminate it by exhausting the ceiling. Observed: 3 rounds of 4/4/2, **6 of the 10 findings authored by the previous round's own fix**; stopped by a human reading the pattern, after the ceiling was raised 3→8. |
| `2026-08-08-19-006` | Re-run the detectors over the **FIX** diff, not only the original. Round 2's findings were direct residue of round 1's own fixes. ⚠ **The delta round has since shipped** (round N+1 reads the previous round's `head_at_completion` as `--since-ref`); the **intra-round** re-scan has not, so a fix's residue still costs a round. A second residual: a delta round's class-closure sweep reaches only the delta surface. |
| `2026-08-08-19-005` | A finding raised **at** the iteration ceiling has no remaining iteration to review its fix, forcing a choice between shipping prose no round examined and shipping a known under-specification. ⛔ Ceiling-iteration findings are systematically less likely to be fixed, and **that bias is invisible in the aggregate "N iterations, M findings, all resolved" summary**. |
| `2026-08-23-22-001` | The surfacer emits `user_facing_strings` with `context: docstring` only. **Assertion messages and comments are covered by no sub-list at all.** Over six rounds on one file, one over-claim was corrected at each site the surfacer could see and kept reappearing at sites it could not. ⛔ The dangerous consequence: **a delta whose entire content is uncovered prose produces a candidate set identical to the previous round's** — round 6's surface was byte-identical to round 5's because the intervening commit changed only assertion messages. |
| `2026-08-24-20-001` | Findings are returned but **not persisted** to `qgate-6-finalize.jsonl`, so the store under-reports what the step found. (Title-only stub — see caveat.) |
| `2026-08-26-05-006` | ⭐ **Seed the candidate surface from the plan's own target defect class.** Two instances in one run of a plan reproducing the class it was chartered to close — one same-document enumeration drift, one intra-plan commit-sequence drift (commit N staled commit 1's own note). Both were found, but by a general sweep of 61 candidates, not because anything knew to look. |

## The one instruction that will NOT work

⛔ `2026-08-26-05-006` states it explicitly and it is worth carrying verbatim: **"Do NOT
convert this into a checklist item for authors."** Its stated mechanism is that *writing the
argument for a defect class is what makes you blind to committing it* — the author holds the
rule as stated rather than as applied, and the sharpest instance sits closest to the prose
that forbids it, which is exactly where a reviewer stops looking. An instruction to "remember
your own rule" is the one remedy the evidence predicts will fail. The remedy has to be
mechanical and pointed at the plan's own theme.

## The cheapest available change

`2026-08-25-15-001` specifies a deterministic self-seeding classifier needing no judgement
and no new data: record each round's fix commit sha (already stamped), diff it against HEAD
at round N+1, intersect with the `file_path` of every new finding, and terminate when the
intersection is **total**. Roughly 15 lines of set arithmetic over data the loop already
holds. ⭐ **It would have fired at round 2 and again at round 3 on the observed run — saving
two of three rounds.** The LLM keeps the judgement it is good at (is this finding real?);
only the termination *classification* becomes deterministic.

## Read-coverage caveat

⛔ `2026-08-24-20-001` is a **title-only stub** — `add` allocated it, `set-body` never ran,
and no body exists. Its membership here rests on its title alone.

## Claim labels

- **OBSERVED** — the five full-body instances, with their round counts, finding ids and
  quoted mechanisms.
- **OBSERVED** — that the delta round shipped and the intra-round re-scan did not;
  `2026-08-08-19-006`'s body states both halves and names what remains open.
- **HYPOTHESIS** — `2026-08-24-20-001`'s persistence gap. Confirm/refute at
  `phase-6-finalize` § `pre-submission-self-review`'s `qgate add` call site, checking whether
  every returned finding reaches `qgate-6-finalize.jsonl`. Verify-at-outline.
- **HYPOTHESIS** — that the self-seeding classifier terminates the loop correctly without
  suppressing genuine late findings. ⚠ Counter-evidence sits in this same cluster:
  `2026-08-25-09-010` (routed to `code-intelligence-substrate`) records a **behavioural**
  defect surfacing at round 6 of 7. A classifier that stops at round 2 must not lose it.
  Confirm/refute with a matched control. Verify-at-outline.

⛔ Counts and finding ids are the filing plans' own and were NOT re-derived here.
