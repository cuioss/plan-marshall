envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T10:23:51Z

component=plan-marshall:phase-3-outline
category=bug
created=2026-10-18

# Verify a Q-Gate premise about file locations against the tree, not against prose

## Context

Outline Q-Gate finding 1a85eb (plan-20-job-runner, deliverable 4) claimed that the native-image metadata of the new FFM kill(2) downcall did not belong in pm-runtime, because "MacSecurity.java documents its downcalls in META-INF/native-image/de.planmarshall/pm-mcp-server-credentials/reachability-metadata.json (assembly repository)". The resolution was recorded as "verified in code", and the outline dropped the metadata file. The premise was wrong: the FFM downcall descriptors of MacSecurity and Posix are registered in pm-runtime/src/main/resources/META-INF/native-image/de.planmarshall/pm-runtime-credentials/reachability-metadata.json. The MacSecurity Javadoc was stale.

The wrong premise cost three functional-review findings and two loop-backs in 6-finalize: c4df5f (false self-report: ADR says registered in the assembly, ADR also says follow-up), 6a1367 (residual: descriptor missing from pm-runtime-credentials), 3c3ebc (false self-report: ADR and Javadoc still reject registering it in pm-runtime). Fix TASK-20 then added the two metadata files outside every declared deliverable surface.

## Root cause

The Q-Gate check and its resolution trusted a Javadoc sentence about where a resource lives. "Verified in code" meant "read the class comment", not "listed the resource tree". A location claim is a filesystem fact; prose about it drifts.

## Proposed action

When a Q-Gate finding or its resolution turns on WHERE a file or resource lives (metadata, config, descriptor), require the resolution to cite the result of a path query (architecture find --pattern on the resource name) rather than a doc or Javadoc sentence. A resolution text that says "verified in code" for a location claim should name the path query it ran.

## Evidence

- qgate 3-outline 1a85eb (resolution taken_into_account, premise false)
- qgate 6-finalize c4df5f, 6a1367, 3c3ebc (functional-review rule)
- retrospective request_result_alignment: "the native-image metadata pair reverses a planning-time decision (finding 1a85eb) that rested on a stale MacSecurity Javadoc"
