# WS-04: The stranded corpus — findings that already exist and are already lost

epic: lessons-routing
status: active

## Charter

Route the findings that are stranded **today**, and establish how many there are.

⭐ This workstream exists because the rest of the epic is forward-looking. A new route does nothing for
a finding already sitting in a git-ignored directory — and at least five such findings were observed
first-party on 2026-08-24 across two of four known consumer repos:

| Repo | Stranded (upstream) | Local |
|---|:--:|:--:|
| `cui-jsf-test-basic` | **3** — `plan-marshall:recipe-refactor-to-profile-standards`, `plan-marshall:build-maven`, `plan-marshall:workflow-integration-sonar` | 1 |
| `API-Sheriff` | 0 | 2 (both prefixed, both mis-classified as foreign) |

⛔ **Two of four known consumer repos were sampled. The population is NOT five** — it is at least five,
over a denominator that has not been enumerated.

## In scope

- Enumerating the real corpus across every consumer repo, with the population stated.
- Reading the stranded upstream findings and routing them — they are real findings about this project
  that nobody here has read.
- Establishing HOW they were filed despite the guard (with `--allow-foreign-store`, or before it
  existed). ⚠ The answer decides whether the guard is routinely bypassed in practice.

## Out of scope

- Building the route (WS-02 owns it). ⛔ **This workstream runs LAST**: migrating a stranded finding
  before a destination exists moves it from one dead end to another.

## Done when

Every pre-existing finding in every known consumer repo has been enumerated, classified, and either
routed or explicitly retired — with the population published, not implied.
