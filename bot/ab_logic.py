from __future__ import annotations

import random

from db import Database


GROUP_TEST = "test"
GROUP_CONTROL = "control"


async def assign_group(db: Database) -> str:
    counts = await db.get_group_counts()
    test_count = counts.get(GROUP_TEST, 0)
    control_count = counts.get(GROUP_CONTROL, 0)

    if test_count < control_count:
        return GROUP_TEST
    if control_count < test_count:
        return GROUP_CONTROL
    return random.choice([GROUP_TEST, GROUP_CONTROL])
