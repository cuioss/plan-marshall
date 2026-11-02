envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T13:55:55Z

# Candidate lesson: Outline consumer sweep missed doc-citation and parallel-helper-list consumers (plan-marshall:phase-3-outline)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-40-validator-terminal-edge-protocol-rules (PR cuioss/API-Sheriff#485), source message 001.


**Source**: 3-outline Q-Gate, findings 3b749e, c83fbf, 58e705, dde544 (all taken_into_account by re-opening 3-outline).
**Probable owner**: plan-marshall:phase-3-outline (consumer-sweep guidance); project angle for API-Sheriff outlines that move tests/members.

## What happened

The outline moved/renamed test classes and members (ConfigValidatorRedirectTest -> rule/TerminalActionRulesRedirectTest, ConfigValidatorTest.WebSocketOriginAllowlist -> rule/ProtocolRulesTest) and extended one helper enumeration (RuleSupport class Javadoc). Its consumer sweep, logged in decision.log, enumerated code references only. The Q-Gate then found four consumers the sweep had not covered:

- `doc/security-threat-model.adoc` lines 1690 (GW-13) and 1478 (GW-09) cite the moved test classes as evidence for a security control.
- `WebSocketProxyIT.java` class Javadoc (line 60) points at ConfigValidatorTest for the boot-refusal proof.
- Two other lists of the same RuleSupport helpers (`rule/package-info.java` lines 24-26 and the ConfigValidator class Javadoc lines 97-99) were left behind while the main one was extended.

## Corrective rule (candidate)

When an outline moves or renames a test class, nested test class or member, the consumer sweep must also search prose for it: `doc/**/*.adoc` (especially `doc/security-threat-model.adoc`, which cites tests as control evidence), Javadoc in other modules (integration-tests ITs), and `package-info.java`. When an outline extends one list that enumerates a set (helpers, rules, modes), it must find and update every other list of the same set, or record that those lists are deliberately incomplete.

## Cost

One extra outline revision round (3 files added across D4/D5) before 4-plan could start.
