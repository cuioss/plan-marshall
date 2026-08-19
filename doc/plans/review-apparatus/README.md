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
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`,
and so — in smaller, disjoint ways — do `520`, `560` and `570`; check each plan's own § Expected
surface rather than assuming this pair is the whole set. **For the passages below, this table is the
single authority for who writes what.** Each plan references it and restates
none of it — a split described in two documents is a split that goes stale in one of them, which is
exactly how this boundary was stated wrongly four times in succession.

| Passage | Gap id | Written by |
|---|---|---|
| The currency-rule scope sentence | `010 G2` | `500` |
| The "by definition an observation at the merge candidate" claim in § "Evidence for a bot that edits one comment in place" | `010 G3` | `500` |
| The § "Consumers" rows for fields `500` adds | — | `500` |
| The new bounded-gap section | — | `500` |
| The records D0 writes: whether a timestamp-anchored completion arm is correct for a wait, and the classification of the sites that decide whether a comment is new information | — | `500` |
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

**Three checks keep this from drifting, and each can fail.** Run them against `500` and `510` before
either is handed to a session. Check 1 is the one that matters: an earlier version tested only
whether a named passage *appeared* in the table, which is why it caught one of three known defects —
presence was never the question, **agreement with the `Written by` column** is.

1. **Every contract passage a plan names, it names in the role this table gives it.** For each
   passage row, find **every** occurrence of it in each plan — not the first; a first-occurrence test
   is satisfied by a legitimate deferral and never reaches the offending mention below it, which is a
   guard that cannot fire. The plan in `Written by` may name it freely. **Every occurrence in any
   other plan MUST carry the literal phrase `per the README table`** — that token, not a paraphrase,
   so the check is a grep rather than a judgement. A plan listing a passage in its § Expected surface,
   or under a *Done when* it must satisfy, is claiming to write it, so an unmarked mention there is a
   failure. Test the assignee, not the mention.
2. **Every contract passage a plan writes has a row here.** A passage a deliverable writes and this
   table does not name is owned by nobody — the defect that took four rounds to find. Read the
   deliverable bodies for this, not the Notes.
3. **Neither plan assigns ownership.** Grep both for `owns` / `owned by` / `belongs to` in a sentence
   that also names a contract passage. The only permitted hit is a pointer *to this table* naming no
   passage. Any other hit is a second copy of the split, and a second copy is what goes stale.

Checks 1 and 2 are read against the **deliverable bodies and § Expected surface**, because that is
where every instance of this defect has actually lived. Phrases in the table are paraphrases; match
on the passage, not on the wording.

**What these checks are worth, measured rather than asserted.** Three defects this boundary actually
produced were re-introduced into scratch copies and the checks run against them:

| Defect | Caught by |
|---|---|
| A plan's ⛔ stating a passage is "owned by" the other plan, on a false premise | check 3 (grep) |
| A *Done when* whose clause covers a passage the plan defers | check 1 (grep, marker absent) |
| § Expected surface listing a passage the table assigns elsewhere | check 2 — **and not by grep**: the neighbouring legitimate deferral supplies the marker |

So **check 2 is not optional and is not a grep**: it is a row-by-row reconciliation of this table
against each plan's § Expected surface, and it is the only one of the three that catches the last
shape. The table is short and the surfaces are short; do it by reading. A grep alone reports clean
over that defect — which is the failure mode this whole epic is named after, so do not let the
tooling stand in for the reconciliation.

The same rule is why **neither plan counts the passages or sites of this shared document**: every
falsehood this boundary produced was a stale numeral. That set is re-derived from `010 gaps.md`
§ Where at the moment of the claim, and written down neither here nor there. The rule is scoped to
this document — a count elsewhere in a plan is fine where it names its members in the same breath,
so a reader can check it without leaving the sentence.
