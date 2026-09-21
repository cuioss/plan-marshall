# WS-06: Context Economics — what a byte costs, and for how many turns

epic: code-intelligence-substrate

> Charter document for one workstream. Created 2026-08-09 from the PLAN-CIS-031 landing,
> whose six-phase instrumented `metrics.toon` was the first record able to decompose the
> cost. See `persona-marshall-orchestrator/standards/orchestration-model.md`.

## Charter

WS-01/02/03 answer *what the system knows about the codebase*. WS-04 answers *whether the
instrument tells the truth*. Neither answers **what context costs and why**, and the
measurement now says that is where the money is.

The epic's founding premise was that exploration of the **codebase** is the addressable
cost. Measured across all six phases of one instrumented plan, the codebase-addressable
share is **15.9%** of exploration bytes, while **65.2% is doc-residency** — the system
reading its own skills, standards and workflow docs. Multiplying by exploration's ~77%
share of tool-result bytes: **roughly half of every tool-result byte is plan-marshall
reading plan-marshall.**

This workstream owns that half, plus the second factor the same data exposed: cost is
`resident_bytes × turns_resident`, and **turn count is a variable nothing in the epic
owns**. It closes when both factors are instrumented, both have a landed lever, and the
epic's value case has been restated against what was measured rather than what was assumed.

## Scope

- **In scope**: the admission-control discipline applied to plan-marshall's **own corpus**
  (skill bodies, `standards/*.md`, workflow docs) — partial loading, ranked retrieval,
  section-granular reads; **dispatch envelope length** and the per-dispatch isolation
  rationale; the `doc/concepts/token-management.adoc` § 6 argument that defends isolation
  in a currency the instrument does not measure.
- **Out of scope**: the *codebase* substrate (WS-01/02/03 own Tier 0/1/2); whether the
  instrument's numbers are trustworthy (WS-04); detector correctness (WS-05). This
  workstream **consumes** WS-04's figures and never repairs them.

⛔ **The binding anti-goal, inherited from the #1069 effort analysis**: every lever here
must reduce **bytes that buy nothing** or **turns a byte needlessly survives**. A lever
whose mechanism reduces to *examine less* is rejected on that ground, not weighed.
Loading a smaller slice of a standard is admission control; loading fewer standards
because examination is expensive is not.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-CIS-039-corpus-residency-admission-control | staged | The 65.2% bucket: the system reads its own corpus whole. |
| PLAN-CIS-040-envelope-length-and-the-isolation-currency | staged | Cost is `bytes × turns`; the turn factor is unowned and § 6 defends isolation in the wrong currency. |

## Sequencing and Surface Notes

- **CIS-039 and CIS-040 are mutually disjoint and MAY pair**: 039 lands on skill/standard
  loading (`ref-workflow-architecture` skill-loading contract, `execution-context`
  Step 3); 040 lands on dispatch granularity and `doc/concepts/token-management.adoc`.
  ⚠ Both touch the `execution-context` agent body — **re-verify the file set at emit**.
- ⛔ **Neither may pair with `PLAN-CIS-042`** (WS-04), which changes what
  `manage-metrics` emits: 039 and 040 both read those fields to size themselves, and a
  plan reading a field a concurrent plan is redefining is the two-writers shape this epic
  keeps filing. **Sequence CIS-042 first** where a figure is load-bearing.
- ⭐ **CIS-041 (WS-03, the LSP in execute) is the mechanism that makes CIS-039 cheap.**
  A live language-server client in the execute envelope is the same protocol shape
  CIS-039 needs to point at the corpus. **Coordinate; do not fork a second client.**
- ⚠ **CIS-039 overlaps PLAN-CIS-007's subject matter** (a language-server surface over the
  skill corpus) from the cost side rather than the editor side. CIS-007 is a Tier-2
  accelerator for humans in an editor; CIS-039 is a token lever for dispatched leaves.
  **Re-verify at outline that they are not building the same index twice.**
