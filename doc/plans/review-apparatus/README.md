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

`500` and `510` contend on one seam and MUST NOT run concurrently.

### The shared-document split

Both plans edit
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`.
**This table is the single authority for who writes what.** Each plan references it and restates
none of it — a split described in two documents is a split that goes stale in one of them, which is
exactly how this boundary was stated wrongly four times in succession.

| Passage | Gap id | Written by |
|---|---|---|
| The currency-rule scope sentence, and the "today, only PR-Agent" statements that qualify it | `010 G2` | `500` |
| The "by definition an observation at the merge candidate" claim in § "Evidence for a bot that edits one comment in place" | `010 G3` | `500` |
| The § "Consumers" rows for fields `500` adds | — | `500` |
| The new bounded-gap section | — | `500` |
| The "stored finding, or … the noise sidecar" two-source arm | `010 G4` | `510` |
| The "edited in place (`updated_at` differs from `created_at`)" arm | `010 G4` | `510` |
| The "union of the stored-finding SHAs and the recorded sidecar SHAs" paragraphs, **including the "observation sidecar" naming inside them** | `010 G4` | `510` |
| The advance-disclosure sentence | `120 G6` | `510` |
| The § "Consumers" row for fields `510` adds | — | `510` |

**The one overlap, resolved here rather than in either plan.** `010 G4` § Where names
`bot-participation-contract.md:491-498` and `010 G11` § Where names `:493-500` — the same paragraphs.
The **paragraphs are `510`'s** (`G4` deletes the union claim that is their subject); `500` renames the
*code* artifact those paragraphs describe (`G11`) and does **not** edit them. Whichever plan runs
second finds the other half done: `510` describes the ledger under whatever name the code then
carries, and `500` reports the prose dependency instead of editing it.

Line numbers here are **leads** — re-derive each passage by its quoted text, not by its line.

A passage this table does not name is settled by neither plan: **report it, do not choose.**

**Two checks keep this from drifting, and both can fail.** Run them against `500` and `510` before
either is handed to a session:

1. **Every contract passage either plan names appears in this table.** Grep each plan for its quoted
   passage phrases and confirm each occurs here. A passage named in a plan and absent from the table
   is a passage owned by nobody — the defect that took four rounds to find.
2. **Neither plan assigns ownership.** Grep both for `owns` / `owned by` / `belongs to` within a
   sentence that also names a contract passage. The only permitted hit is a pointer *to this table*
   that names no passage. Any other hit is a second copy of the split, and a second copy is what goes
   stale.

The same rule is why **neither plan counts the passages or sites of this shared document**: every
falsehood this boundary produced was a stale numeral. That set is re-derived from `010 gaps.md`
§ Where at the moment of the claim, and written down neither here nor there. The rule is scoped to
this document — a count elsewhere in a plan is fine where it names its members in the same breath,
so a reader can check it without leaving the sentence.
