envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T07:45:14Z

# FORWARDED CLUSTER — the lookup substrate itself: search, caller-graph, and a live path defect

**Forwarded from `truthful-signals` 2026-07-29 under the inbound routing rule** (how the system knows
things → this epic). ⚠ **Leads, not facts.** ⭐ **This is the cluster that speaks DIRECTLY to the
epic's pending direction decision — read it before `decompose`.**

| Source message | Origin | Claim |
|---|---|---|
| `runnable-slice-keys-…-005` | PLAN-89 / #1044 | **A field-name sweep cannot find a caller-graph hit** |
| `exploration-share-is-unmeasured-002` | PLAN-99 / #1043 | `audit.py`'s `write_persisted_report` derives its path from `Path.cwd()` and **ignores `--plan-dir`** |
| `exploration-share-is-unmeasured-009` | PLAN-99 / #1043 | The chat-history aspect reported **full-analysis Tier 1 after keeping 2 of 1156 turns** |

## ⭐ Why `runnable-slice-…-005` is direction-relevant evidence

*"A field-name sweep cannot find a caller-graph hit."* This is the **empty-graph problem stated from
the consumer's side.** A text sweep over a field name finds declarations and mentions; it cannot find
*who calls what*. That is precisely the derivation a real graph would supply — and
`architecture graph` currently returns **0 edges** (orchestrator-verified: 12 nodes, 0 edges,
`impact` empty for every module).

⇒ **It is independent evidence for direction C (LSP) or D (a symbol index) over direction B (a graph
backend):** the gap is *deriving* the caller graph, and a storage/traversal library derives nothing.
It also bounds the cheapest option honestly — **restoring `Grep` to leaves fixes content search but
would NOT have found this hit either.** ⚠ **Record that limit at `decompose`**: the cheap fix and the
substrate question are not the same question, and this message is the cleanest proof.

## ⛔ A LIVE PRODUCTION DEFECT needing allocation

`audit.py write_persisted_report` derives its output path from `Path.cwd()` and **ignores
`--plan-dir`**. **TASK-11 fixed only the TEST side**, so the production path is still wrong.

⚠ **This is the fix-the-test-not-the-call inversion**: the test-side fix makes the surface green
while the defect stays live — indistinguishable, from the outside, from a real fix at the reporting
layer. **No plan in either epic owns it. Recommend allocating it**, most naturally onto
**PLAN-76 `auditor-detector-integrity`** (same file), which is already 6D at the split guard — so
weigh adding it against splitting PLAN-76 rather than growing it.

## The third item

`exploration-…-009`: the chat-history aspect **reported Tier 1 full analysis after keeping 2 of 1156
turns** — a 0.17 % sample reported as full coverage. ⭐ **The volume-read-as-coverage archetype in its
most extreme observed form.** Owner: **PLAN-78 `chat-signal-provenance-filter-under-inclusive`**,
already in this epic's queue. **Fold as its sharpest instance.**
