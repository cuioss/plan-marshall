#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``list stalled`` test module.

Holds the module-level loads, constants and helpers it uses, so
the module itself carries the import and not the preamble.
"""


import json


def _write_lesson_plan(tmp_path, plan_id, lesson_ids, plan_source,
                       current_phase, phase_status):
    """Create a plan dir holding relocated lesson files plus a status.json.

    ``plan_source`` is written verbatim into ``metadata.plan_source`` so tests
    can exercise lesson-id-shaped, non-lesson-id, and unset values — none of
    which affect membership, since the population is derived from the lesson
    file's presence. The ``phases`` list carries a single row for
    ``current_phase`` with the supplied ``phase_status`` (mirroring the real
    status.json shape).
    """
    plan_dir = tmp_path / 'plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)

    for lesson_id in lesson_ids:
        (plan_dir / f'lesson-{lesson_id}.md').write_text(
            f'id={lesson_id}\ncomponent=test\ncategory=bug\ncreated=2025-01-01\n\n'
            f'# Lesson {lesson_id}\n\nBody.\n'
        )

    status = {
        'plan_id': plan_id,
        'current_phase': current_phase,
        'phases': [{'name': current_phase, 'status': phase_status}],
        'metadata': {'plan_source': plan_source},
    }
    (plan_dir / 'status.json').write_text(json.dumps(status))
    return plan_dir
