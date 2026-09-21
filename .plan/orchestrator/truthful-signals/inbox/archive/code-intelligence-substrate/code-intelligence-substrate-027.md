envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=truthful-signals
kind=finding
created=2026-09-05T13:55:40Z

envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=truthful-signals
kind=finding
created=2026-09-05T13:54:58Z

## A plan spec's own gating-derivation premise is confidently false

**Source**: `code-intelligence-substrate` epic, spec `PLAN-CIS-054-documentation-surface-truthfulness.md`, § D6 "The epic's own plan-directory records" → the re-expressed (2026-08-24) gating derivation.

**The claim, as written and trusted at face value**: the spec's corrected D6 gating derivation states, as settled fact and the premise for disarming a "vacuous-pass trap":

> "That directory IS absent entirely" — referring to `.plan/local/orchestrator/code-intelligence-substrate/cloud-runs/`.

**What is actually true at HEAD `28b578f1ed435973e53c510f0c8225446cc024aa`**: the directory is present and populated. A read-only re-grounding pass directly `Read` three of its per-source-plan `gaps.md` files and all three exist with real content:

- `.plan/local/orchestrator/code-intelligence-substrate/cloud-runs/030-attribution-populations-and-the-cost-decomposition/gaps.md`
- `.plan/local/orchestrator/code-intelligence-substrate/cloud-runs/020-corpus-residency-admission-control/gaps.md`
- `.plan/local/orchestrator/code-intelligence-substrate/cloud-runs/290-auditor-detector-integrity/gaps.md`

This is independently corroborated by the epic's own already-persisted ledger verdict for CIS-054 (`orchestrator corpus verdicts`, producer `code-intelligence-substrate/cleanup`, `checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa`): *"its § D6 body premise 'That directory IS absent entirely' is FALSE; three cloud-runs gaps.md files were read directly and are present, so D6 would take the discharged-by-collection fallback it exists to disarm."*

**Why this is a `truthful-signals` finding rather than staying epic-local**: this is not a defect in application code or in a skill's documentation of behavior — it is a *governing document about how to interpret evidence* (a plan spec's own gating derivation) making a confident, unhedged absence claim that a single direct read refutes, sitting inside the authoritative instrument a reader/executor is told to trust without re-deriving. That is the confident-signal-hides-a-caveat archetype, recurring INSIDE a document whose entire purpose is finding exactly this defect class in other documents. It also carries live blast radius: had D6's gating derivation been executed exactly as written (list the directory; treat absence as `discharged-by-collection`), a real executor would have wrongly discharged roughly forty unexamined defects as a clean pass over a directory that was never actually empty.

**Likely root cause, stated as a hypothesis, not verified here**: `.plan/local/` is git-ignored, so a genuinely fresh clone would not carry `cloud-runs/`, which is probably what motivated the "IS absent entirely" framing. But the sentence is written as an unconditional fact about the tree rather than as a claim conditioned on clone/session state, and no hedge or re-check instruction accompanies it — exactly the vagueness this theme tracks.

**Disposition**: no repository code fix is implied. The correction belongs to whoever next reworks `PLAN-CIS-054`'s § D6 (code-intelligence-substrate's own remit, tracked in that epic's own ledger — its already-persisted verdict already carries this exact finding). This message is filed here only because the *pattern* — a confident, unchecked absence/non-existence claim embedded in a governing or gating document — is `truthful-signals`' cross-cutting remit, not because the fix itself belongs to this epic.
