envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=truthful-signals
kind=finding
created=2026-08-26T21:12:40Z

# Doc-contract divergence: a documented surface the live one rejects or contradicts

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule.

**Cluster:** 15 lessons. ⚠ **Expect to split this** — it is one coherent failure mode but
well past the scope-bloat guard. **Suggested fold target:** `PLAN-TRUTH-012` if it still
holds this surface; otherwise split by sub-shape (the three below are natural cuts).

## The failure mode

A document states a contract the live surface does not implement. The document reads as
authoritative, nothing binds the two, and the divergence is found the expensive way — an
agent hitting the rejection at runtime, mid-phase, one at a time.

## Sub-shape A — a documented invocation the parser rejects (5)

| Lesson | Instance |
|--------|----------|
| `2026-08-23-16-001` | `triage.md` § Step 3c prescribes `deliverable: 0`; the validator's falsy check rejects it as *"Missing required field"*. **Every fix task allocated through the documented FIX path hits this.** The workaround fabricates provenance — the task claims a deliverable it has nothing to do with. |
| `2026-08-24-12-002` | `branch-cleanup.md`'s merge-barrier example passes `--measured-diff-size` unconditionally; with no refusals the value is empty, the executor strips empty-string args, and argparse rejects the bare flag. ⛔ **Inside a fail-closed merge gate** — the honest outcome is a merge blocked by the documentation of the block. The doc's own prose already explains the `nargs='?'` defence for the eight list flags beside it and interpolates all nine identically. |
| `2026-08-25-09-008` | `plan-retrospective` Step 5b names `plan-marshall:marshall-orchestrator:orchestrator`; the live notation is `plan-orchestrator`. **Every orchestrated plan's retrospective fails at its recording step**; non-orchestrated ones take the other branch, which is why it survived. |
| `2026-08-08-20-003` | `manage-logging read --phase` is declared with a constrained `choices` list, validates its input, and **applies no filter**. The inverse of argparse-rejection drift: the advertised surface is *wider* than the implementation and the call succeeds wrongly. `total_entries` reports the unfiltered population either way, so the count that would expose the no-op corroborates the wrong answer. |
| `2026-08-08-19-001` | The archived-plan audit's argparse-rejection corpus — 463 signatures across 48 of 58 plans. (Unresolvable — see caveat.) |

## Sub-shape B — a stated constraint the mechanism cannot satisfy (5)

| Lesson | Instance |
|--------|----------|
| `2026-08-24-09-001` + `2026-08-26-13-001` | **One defect, observed twice.** `automatic-review`'s Branch A `display_detail` template renders 86 chars with a non-ASCII em dash against the same document's stated `<=80 chars, ASCII` cap. Structural, not a typo: `review_state_summary` is unbounded and grows with the bot roster, so no fixed template ending in `(unified triage pending)` can honour the cap. Fires on the **three-bot roster this repo actually ships**. |
| `2026-08-24-08-002` + `2026-08-25-06-001` | **One defect, observed twice.** `pr_intent_section render` APPENDS the Intent block while `pr-template.md` declares a mid-body slot, so Intent lands below the footer on **every** finalize-generated PR. The second observation adds that the render is also non-idempotent and truncates at the char budget, losing non-goals. |
| `2026-08-26-05-007` | A docstring enumerated **three** conditions returning `False`; the body implemented two. The missing one was "timestamps that do not compare" — and `<` on strings is **total**, so it always yields a verdict. Mixed ISO-8601 offsets then sort by wall-clock digits rather than by instant, silently **inverting** the ordering, in the arm that errs toward crediting participation. ⭐ Its fix is the model: a pinned comparable-shape constant, plus 8 tests including a **matched positive and negative control**, with the pre-fix run recorded verbatim. |

## Sub-shape C — a declared key space or producer that does not exist (5)

| Lesson | Instance |
|--------|----------|
| `2026-08-26-08-001` | `data-model.md` says the lane value is *"validated by `validate_lane_override`"*. Only `finalize-steps set-lane` validates; the generic `plan <phase> step set --param lane` path writes the same field with no enum check and **accepted and persisted `auto`**. Both verbs write the same field, so a reader cannot tell which path they are on. |
| `2026-08-25-09-011` | The plan-efficiency anchor table enumerates `bug_fix`/`feature`/`refactor`; `manage-status change-type-heuristic` emits `enhancement`. A plan carrying an unlisted `change_type` is **structurally incapable** of tripping an absolute token anchor. |
| `2026-08-25-09-013` | Two of fifteen declared report sections have **no producer**. `executive-summary` is not in the aspect registry at all; `dispatch_boundaries` is in the registry but in no documented step, while `analyze-logs` emits that data nested where the compiler does not look. Both land in `sections_omitted`, which the spec defines as *"benign: nothing was lost"*. It was a **drop reported as an omission**. |
| `2026-08-25-09-009` | `plan-retrospective`'s Input Contract declares `orchestrated`/`epic` as forwarded and states the body **MUST NOT recompute** them. The dispatcher sends neither. A body obeying the prohibition falls through to the default `false` — the branch that writes to the **global lessons store** instead of the epic inbox. Silent in both directions. |
| `2026-08-23-13-002` | `scope_creep_threshold` is documented as a `marshal.json` override in two places, and `scope_creep_check` never reads config at all. (Unresolvable — see caveat.) |

## The one lesson that generalises the class

`2026-08-24-12-002` states it: **a documented invocation that interpolates a placeholder must
state what happens when that placeholder is empty**, because the executor's empty-strip makes
"empty" and "absent" indistinguishable at the parser. Quoting does not save it; the quotes
never reach argparse.

⚠ **The analyzer that owns this class cannot see it.** `2026-08-24-09-002` records
`scan_manage_invocation` reporting `findings: 0` while four divergences of exactly this class
sat live in the tree it had just scanned, and names those four as its regression corpus. That
lesson is routed separately (empty-population cluster) but the two meet here.

## Read-coverage caveat

⛔ Four rows were not read from a body:

- **Title-only stubs** (`add` ran, `set-body` never did): `2026-08-25-06-001`,
  `2026-08-26-13-001`. Their titles carry the finding; nothing else exists.
- **Unresolvable** (`list` says `active`, `get` says `not_found`): `2026-08-23-13-002`,
  `2026-08-08-19-001`. `23-13-002`'s subject comes from its `list` title;
  `19-001`'s comes from `2026-08-08-20-002`'s second-hand description of it, since its title
  is also empty. **`19-001` is the weakest row in this cluster** — nothing in this run read
  either its title or its body.

## Claim labels

- **OBSERVED** — the eleven full-body instances, each with the quoted rejection or the
  quoted contradicting text.
- **OBSERVED** — that `24-09-001`/`26-13-001` and `24-08-002`/`25-06-001` are each one
  defect observed twice; the pairs' titles and bodies name the same site and mechanism.
- **HYPOTHESIS** — the four title/second-hand-derived rows belong here. Confirm/refute at
  the lesson files once the corpus-integrity defect is fixed. Verify-at-outline.
- **HYPOTHESIS** — that sub-shapes A/B/C are the right split. They are this router's cut,
  not a property of the corpus; adopt or re-cut freely.

⛔ Counts and site references are the filing plans' own and were NOT re-derived here.
