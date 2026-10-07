envelope_version=1
sender_type=plan
sender_id=test-suite-anti-vacuity
epic=truthful-signals
kind=finding
created=2026-09-07T11:20:02Z

# Three confident-signal defects observed on PR #1430

All three surfaced during plan `test-suite-anti-vacuity` (PR #1430) and are
live on main, not specific to that plan. Each is the epic's theme exactly: a
signal that reads as settled while the thing it reports is not.

## 1. `review_completeness` credits a bot that refused in the same invocation

`review_completeness` returned `participation_complete: true` with
`coderabbit: participated`, while the **same invocation** carried coderabbit in
`--refused-bots` with `cause=quota` and assigned it no refusal member at all
(`refusal_causes[]` named only sourcery). A refusal is therefore silently
outranked by a stale prior publish. Confirmed twice, on two separate HEADs.

**The mechanism is self-perpetuating and will not clear on its own.** A first
bad `participated` credit records the then-current merge-candidate SHA into the
currency ledger. On every later pass the SHA-currency arm's test — *"the SHA
recorded at the last credit IS the merge candidate"* — then holds trivially and
re-credits the bot, with `stale_participation_bots[]` coming back empty. Only a
HEAD advance that supersedes the recorded SHA breaks the loop; on this PR a
rebase did that incidentally, which is the only reason the truth surfaced.

One premise correction worth carrying, because it sends the fix to the wrong
file otherwise: coderabbit declares `participation_requires_update: **true**`,
not false — its summary comment is edited in place on re-review. The currency
test does apply. It passed anyway, for the ledger reason above.

Site: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
Plan-store hash: `c562f9`

## 2. `_BUILD_CLASS_PREFIXES` is a hand-maintained mirror of `_BUILD_NOTATIONS`

`execute-script.py.template` declares `_BUILD_CLASS_PREFIXES` separately from
`_BUILD_NOTATIONS`. A new build notation added to the latter without a matching
prefix makes `_is_build_class_notation()` return `False` for its run dispatch,
so the executor skips `_append_build_ledger_record()` and a completed build
leaves **no `kind=build` ledger entry**.

The downstream cost is concrete: `pre-commit-verify-freshness` reads exactly
those rows, so a build that ran and passed would be invisible to the freshness
gate — a silent false negative in a gate whose whole purpose is to establish
that a build happened.

Remedy shape: generate the prefixes from `_BUILD_NOTATIONS` at
executor-generation time, or move both consumers to one shared declaration.

Site: `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template`
Plan-store hash: `08a95a`

## 3. Executor bootstrap timeout is uncoupled from `PM_SURFACE_BUDGET_SECONDS`

`test/conftest.py::_ensure_executor_present` runs the generator with a fixed
`timeout=300`, while the generator itself lets `PM_SURFACE_BUDGET_SECONDS`
raise its `180.0`s default. That budget covers only accept-set derivation —
discovery and the atomic write run **after** it.

Raising the budget past the fixed timeout makes `subprocess.run` raise
`TimeoutExpired` and `_ensure_executor_present` raise `ExecutorBootstrapError`,
aborting test startup even though generation stayed inside its own configured
budget. Two numbers that are a coupled pair, maintained independently — the
same mirror archetype as (2).

Remedy shape: declare the budget-to-timeout relationship once with an explicit
margin and have both paths read it.

Sites: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py`,
`test/conftest.py`
Plan-store hash: `fa3545`

## Provenance

(2) and (3) were CodeRabbit outside-diff review-body comments on PR #1430,
filed individually so they are durable and routable rather than buried in a
review body. All three were dispositioned `taken_into_account` in the
originating plan as out of scope for a test-falsifiability change set.
