# Audit of the landed code-intelligence-substrate plans

A ground-truth audit of every landed plan in this epic, and the fix plans derived from it.

⚠ **This directory holds records, not a plan** — no `plan.md`, no `report-NN.md`. Read it as the
account of how the `5xx` fix plans came to exist.

⛔ **The collect step does not yet know that.** `doc/plans/cloud-bridge.md` § Path 3 step 1 states
without qualification that *every* directory under an epic is a plan a run has worked, and the
`_`-prefix convention it would need is documented only for the **epic** level
(`doc/plans/README.md`, on `_template/`), never for a directory inside one. `_audit/` is the first
such directory in this repository.

The bound, stated because the run owes it rather than left for a reader to derive: § Path 3 step 2
records nothing without a merged PR **and** a `report-NN.md`, and step 6 deletes only what steps 2–5
corroborated. `_audit/` has neither, so a collector following the steps reaches an unhandled case and
**stops** — it cannot record a false landing and cannot delete anything. Extending the contract to
exclude `_`-prefixed directories explicitly is a change to the governing contract, which this run may
not self-approve, so it is raised as a proposal in `570-cloud-plan-lane-contract-proposals.md`.

## What was audited

All 36 landed plans (`010` … `350`), each carrying its `plan.md` and at least one `report-NN.md`.
Each was checked against the tree it left behind, not against its own account of itself.

Two artefacts were written into each plan's own directory:

| File | What it holds |
|---|---|
| `verification.md` | Per-deliverable verdict against the tree, correctness review, test adequacy, report accuracy, residue status, and the method used to reach each |
| `gaps.md` | Every defect as an actionable entry — kind, severity, topic, `path:line`, evidence, consequence, action, observable *done when*, effort, risk if fixed |

Each pair was then attacked by an independent reviewer that had not produced it, across eight
classes: fabricated findings, missed findings, vacuous evidence, wrong counts and quotes,
unactionable entries, mis-calibrated severity, coverage holes, and internal inconsistency. Its
result is appended to each `verification.md` as `## Adversarial review`.

## What the audit found

| Verdict | Plans |
|---|---|
| CONFIRMED WITH GAPS | 33 |
| PARTIALLY REFUTED | 2 |
| PARTIAL | 1 |

No plan was found to have shipped nothing, and no plan was found wholly sound. **472 gaps** were
recorded — **46 high, 216 medium, 210 low**, counted from the `Severity` field of the entries
themselves.

⚠ **No fix plan re-rates a gap; every plan carries the severity its entry carries.** This is worth
stating because an earlier roll-up here said otherwise. Two entries —
`200-lsp-derivation-resolver/gaps.md#G13` and `310-main-sha-records-the-pinned-cwd/gaps.md#G1` — are
rated **medium** by their entry *and* by their adversarial review, and an earlier count read both as
high: a parsing error over severity lines containing the word "high" in prose ("*Raise to high if…*",
"*why medium and not high*"). Plan `500` then briefly escalated `200/#G13` on the trigger its entry
names, on a justification that did not hold, and that escalation is withdrawn — see `500` § Notes.
Re-derive these figures from the `Severity` field of the entries rather than trusting this paragraph.

### The recurring defect

The epic exists to make token-reduction claims verifiable. Its own instruments repeat one shape:
**a confident verdict published over a population the instrument never examined.** Not a crash, not
a wrong number — a *clean* signal where there is no evidence for one:

- a freshness verdict read from an index snapshot rather than from the document it describes, so a
  module with no document at all reports `fresh` with a description;
- a capability reported `not_derivable` while the query it gates returns a real result;
- a discriminator whose fall-through branch is documented as proof of the thing it fell through
  from, so three distinct inputs — including a measurement that failed — collapse into one verdict;
- waste figures summing a column whose writer defaults it to zero, mixing measured spend with
  fabricated zeros;
- a duration total published at one precision beside shares computed at another, so a corpus
  totalling `0.0 s` carries a row owning `100 %` of it.

The second recurring shape is its enabler: **a guard that cannot fire.** Tests asserting their own
output back to themselves, canaries whose trigger condition can never match, corpora where a large
share of checks pass with every attribute stripped, and — twice — a shipped test that pins the
defect as correct behaviour.

The third is documentary: a claim corrected at the site a reviewer pointed to and left standing
everywhere else it is asserted, including one commit that fixes a sentence and leaves the same
sentence nine hundred lines above it in the same file.

### What the adversarial pass changed

It was not a formality. Every one of the 36 reviews returned *sound after correction* — none
returned sound as written. Beyond citation and count fixes, it:

- **recovered three proved gaps, two of them high, that were cited in a `verification.md` but never
  written into the `gaps.md` a fix run reads** — they would have been invisible;
- **withdrew a gap's central claim** — `300-freshness-gate-cannot-distinguish-test-authored-evidence/gaps.md`
  § G1, whose evidence was a timing artifact of this shared audit tree (measurements taken while
  sibling agents ran full suites). The claim was struck, the severity lowered to `low` and the action
  narrowed; the entry itself survives and is carried by `560`. As written it would have sent a fix run
  to rewrite correct documentation;
- **executed proposed fixes** and found several would break the suite or were unsatisfiable as
  written — one required breaking a guard the epic had deliberately built and mutation-proven;
- **found defects reachable only by driving the real interface**, notably a protocol surface handing
  an editor unverified reference sites as exact locations, which a CLI-only check could not see;
- **re-aimed a gap at the wrong layer**, where the prescribed action would have violated a shared
  schema and reddened a shipped test.

## The fix plans

Eight plans, numbered from `500`, sparse in tens. Every gap is assigned to exactly one, and each
plan's `## Gap coverage` section names the gap ids it discharges:

| Plan | Gaps | High |
|---|---|---|
| `500-lsp-and-derivation-resolver-correctness` | 28 | 10 |
| `510-architecture-store-query-truthfulness` | 59 | 5 |
| `520-measurement-and-cost-integrity` | 64 | 9 |
| `530-detector-and-auditor-integrity` | 36 | 11 |
| `540-finalize-dispatch-and-blocking-boundary-observability` | 24 | 6 |
| `550-test-suite-anti-vacuity` | 73 | 2 |
| `560-documentation-surface-truthfulness` | 156 | 3 |
| `570-cloud-plan-lane-contract-proposals` | 32 | 0 |

Grouping is by owning surface and shared mechanism. Two departures are deliberate: `550` groups by
*failure shape* rather than by source plan, because the shapes recur across thirty plans and are
what a reader can generalise from; and `570` records proposals rather than shipping amendments,
because the lane contract forbids a run from self-approving a change to the contract governing it.

### Sequencing

Recorded in each plan's Notes, and binding where stated:

- `540` **preferably before** `550` — `550` widens the finalize seam sweep, which is red while
  `540`'s two unmigrated dispatch sites remain, so landing `540` first gets there in one step.
  ⚠ **This is a preference, not a prerequisite.** `550` is order-independent by construction: its D1
  prerequisite probe holds each such item with its test body recorded when the sibling has not
  landed. Do not hold `550` for it.
- `560` **last** — it corrects descriptions of behaviour that the other seven plans change.
- `520`, `530` and `550` must not run concurrently against `audit.py`; `510`, `540` and `550`
  overlap on the architecture and finalize surfaces. These are conflict-avoidance constraints, not
  prerequisites.

### Reading the gap entries

Two cautions carry into any run that picks these up:

1. **Where a gap entry and its adversarial review disagree, the review wins.** It is the later,
   evidence-bearing pass, and the fix plans already carry its corrections.
2. **Any figure derived from a duration or throughput is a lead, not a fact.** The audit ran many
   agents concurrently in one tree; at least one timing-based finding was shown to be contention.
   Re-measure before acting.

The `gaps.md` and `verification.md` files are removed with their plan directories at collect
(§ Path 3). The `5xx` plans therefore restate what a run needs and cite those files as corroboration
rather than as required reading.
