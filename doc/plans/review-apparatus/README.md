# review-apparatus

Plans staged for standalone execution from the `review-apparatus` epic.

**Theme:** the reliability of automated PR review — reviewer participation, comment retrieval,
triage, and the signals that report whether a review actually happened.

Execution contract: `Skill: cloud-plan-lane` (see [`../README.md`](../README.md)).

## Audit of the landed plans

Every plan in this epic that has run carries two further documents alongside its `plan.md` and its
run report:

| File | What it holds |
|---|---|
| `verification.md` | Ground truth: each deliverable's *Done when* checked against the tree, an audit of every load-bearing claim the run report makes, and the correctness, completeness and out-of-scope reviews. Each carries an `## Adversarial review` section recording a second, independent re-derivation. |
| `gaps.md` | What the verification found still open, written as executable tasks — severity, the sites, the evidence, the fix, and an observable *done when*. |

The audit's own findings are staged as the **`5NN-` plan series** in this directory. Those plans
carry the gaps forward grouped by the mechanism they belong to rather than by the plan that
surfaced them, so one seam is repaired once:

| Plan | Seam |
|---|---|
| `500` | Participation credit, anchored to the commit being merged |
| `510` | Refusal and decline accounting, and the contract that describes it |
| `520` | The deficit signal and the comparison grade — telling "nobody reviewed" from "reviewed clean" |
| `530` | CI dispatch enforcement, the exit-code convention, and the envelope contract |
| `540` | What finalize asserts when a plan ends — the landing message and the foreign-PR gate |
| `550` | The review-comment round trip — the noise pre-filter, the reply marker, the agent block |
| `560` | The instruments that measure our own gates |
| `570` | The epic's records, which carry the defect the epic is named after |

`500` and `510` contend on one seam and MUST NOT run concurrently; each names the boundary in its
Notes.
