envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:02:40Z

component=plan-marshall:phase-3-outline
category=anti-pattern

# The outline's carve-out assumption was falsified by measurement — a blanket fixture would have silently deleted coverage

The outline assumed the routing-owning tests were **exactly** `test/plan-marshall/build-server/`. That directory boundary was the carve-out the design rested on: neutralize routing everywhere *except* there.

Measurement falsified it. The real membership is **15 tests, 5 of them outside that directory, spread across four further skills.** The routing seam is owned by more surfaces than the directory name suggests.

Had the plan shipped the assumed carve-out — a blanket `autouse` fixture with a single-directory exclusion — those 5 out-of-directory tests would have been **silently reduced to tautologies**. They would still pass. They would still be counted in the suite total. They would have measured nothing. A green suite is precisely the thing that hides this class of coverage deletion, because the deleted coverage leaves no failing test behind.

## Solution

- **Never let a directory path stand in for a semantic set.** "The tests that own behaviour X" and "the tests under `path/to/X/`" are different sets, and the outline must measure the first rather than assume it equals the second.
- **Enumerate the carve-out membership before designing around it**, and design the mechanism *after* the membership is known — not the other way round.
- Treat any `autouse`/blanket fixture that neutralizes a behaviour as a **coverage-deleting change** by default. Before shipping it, enumerate every test that asserts on the neutralized behaviour and confirm each is either excluded or genuinely unaffected. The exclusion list must be derived, not named.
- Prefer fixture-scoped neutralization at the owning tests over a blanket fixture plus exclusions: the failure mode of a missed exclusion is silent, whereas the failure mode of a missed opt-in is a visible failing test. **Choose the mechanism whose mistakes are loud.**

## Impact

Applies to every autouse fixture, global monkeypatch, blanket mock, and conftest-level environment override. Also a direct instance of the standing rule that a plan's scope assumption must be measured at outline: this one was stated with a concrete directory, which made it read as a fact rather than a hypothesis.
