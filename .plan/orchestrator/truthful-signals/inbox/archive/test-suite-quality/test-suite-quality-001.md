envelope_version=1
sender_type=orchestrator
sender_id=test-suite-quality
epic=truthful-signals
kind=finding
created=2026-07-28T17:42:08Z

# Three CONFIRMED CodeRabbit findings, untriaged and live in main (PR #1036)

Handed over from epic `test-suite-quality` at its close (2026-07-28, 10/10). This epic is the
named owner: the defects are review-machinery residue, not test-suite quality.

## Provenance — why these were never triaged

CodeRabbit was rate-limited at finalize time, the PR merged, the rate window expired, and the
review landed on a closed PR. Timeline:

| Time (UTC) | Event |
|------------|-------|
| 14:41:14 | `coderabbitai` refuses — review limit reached |
| 15:44:05 | answers a manual `@coderabbitai review` with "✅ Review finished" (vacuous — it refreshed its own rate-limit notice 6 s later) |
| 16:35:23 | second commit `530e5fac` pushed |
| **16:42:47** | **PR #1036 MERGED** (`a8cc8acef`) |
| **16:45:29** | **"Actionable comments posted: 5"** — 5 inline findings |

Review base was `741a1c99d..530e5face`, i.e. CodeRabbit reviewed the **final** tree including
the second commit. **All 12 PR comments remain unresolved.**

This is the second consecutive occurrence (#1026 at 58 s post-merge, #1036 at 2m42s), so the
mechanism is causal, not coincidental. Filed as lesson `2026-07-28-19-002`.

## The three CONFIRMED defects

All three were verified against merged main by the `test-suite-quality` orchestrator (read-only
corroboration, not accepted from the bot). All three are inside PLAN-10's own new regression
detectors — the tests written to prevent exactly this archetype.

**1. `test/plan-marshall/phase-6-finalize/test_step_completion_emission.py:136-147`**
`test_enumeration_finds_the_known_bypass_sites` anchors on `('4b', '4c', '5d')` and **omits
item 5** — the dispatch-timeout path that PLAN-10's own *second commit* added as the fourth
structural bypass. The non-degeneracy anchor protects the three bypasses known before the fix
and not the one the fix introduced. If item 5's classification silently breaks, the anchor
stays green.

**2. `test/plan-marshall/plan-retrospective/test_registered_aspects_render.py:100-102`**

```python
path = _SKILL_DIR / rel
if path.is_file() and path not in docs:
    docs.append(path)
```

A roster row naming a document not on disk is silently skipped, removing that document's
dispatches from the scanned population — so the registerability guard passes vacuously. The
docstring **rationalises** it ("the roster-vs-disk consistency of those paths is not this
guard's concern"), which is defending-documentation around a vacuous path: a roster row
pointing at a missing file *is* the roster drift the guard exists to catch.

**3. `test/plan-marshall/phase-5-execute/test_execute_phase_markers.py:64-65`**

```python
_METADATA_SET_RE = re.compile(r'manage-status\s+metadata\b[\s\S]{0,200}?--set\b')
```

Accepts **any** `metadata --set` anywhere in Step 4. The deliverable (D2) was specifically the
`phase_5_first_entry_logged` marker write in the first-entry branch. Remove that write, leave
any sibling `--set` in the section, and the test still passes.

## ⛔ The fourth finding is CONTRADICTED — do NOT action it

CodeRabbit's finding on `agents.md:131` claims D4's count-free wording breaks
`_declared_enumeration_items` in `test_step_termination_contract.py:455-470`.

**It does not.** That detector's regex is:

```python
_COROLLARY_ENUMERATION = re.compile(
    r'This is the \w+ corollary of the leaf/dispatch-topology invariant above '
    r'\(([^)]+)\)'
)
```

It targets the *"This is the {ordinal} corollary of the leaf/dispatch-topology invariant
above (…)"* sentences at `agents.md:127` and `:162`. D4 edited the two **"escalation-envelope
pattern"** sentences at `:131` and `:174` — different sentences, and both parentheticals the
detector reads are intact. Green CI corroborates. **Acting on this finding would break a
working detector.** The fifth finding (prose-only "indivisible pairs") is carried as a watch,
not a defect — see the separate handover message.

## Suggested shape

A single small plan closing all three, since they share one archetype and one root cause
(**a detector's non-degeneracy anchor goes stale when the fix widens the population**, filed
as lesson `2026-07-28-19-006`). Each fix is a few lines. The population rule applies:
extend the anchor in the same commit that widens the population; assert existence rather than
skipping on a missing member; bind the assertion to the specific artifact the deliverable
creates, not its syntactic family.
