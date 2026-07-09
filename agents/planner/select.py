"""Planner implementation switch (BLUEPRINT.md §9 Phase 2/5): selects the
stub or the real (model-calling) planner for a pipeline run. Default is
always stub -- the real planner is opt-in, explicit, never accidental,
so the FI suite and Phase 2 pipeline tests stay green unchanged whether
or not this module is ever imported. Mirrors agents/checker/select.py.
"""
from __future__ import annotations

import functools
import os
import sqlite3
from typing import Callable

from contracts.schemas import ComplianceRule, ViolationFinding

PLANNER_MODE_ENV = "PLANNER_MODE"


def get_planner_fn(
    conn: sqlite3.Connection | None = None,
    run_id: str = "run",
    rules_by_id: dict[str, ComplianceRule] | None = None,
    mode: str | None = None,
) -> Callable[[ViolationFinding], dict | None]:
    """mode, if given, overrides the PLANNER_MODE env var, which itself
    defaults to "stub". mode="real" requires a ledger connection and
    rules_by_id (the real planner's read_rule tool needs the rule text
    for the finding it's bound to; run_plan_stage itself only ever
    passes a bare finding, so rules_by_id is bound here, not threaded
    through the stage runner -- Phase 2's run_plan_stage signature and
    tests stay untouched).
    """
    mode = mode or os.environ.get(PLANNER_MODE_ENV, "stub")
    if mode == "real":
        if conn is None or rules_by_id is None:
            raise ValueError("real planner requires a ledger connection and rules_by_id")
        from .harness import real_planner

        return functools.partial(real_planner, ledger_conn=conn, run_id=run_id, rules_by_id=rules_by_id)
    if mode != "stub":
        raise ValueError(f"unknown PLANNER_MODE {mode!r}, expected 'stub' or 'real'")
    from .stub import stub_planner

    return stub_planner
