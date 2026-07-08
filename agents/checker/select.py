"""Checker implementation switch (BLUEPRINT.md §9 Phase 2/3): selects the
stub or the real (model-calling) checker for a pipeline run. Default is
always stub -- the real checker is opt-in, explicit, never accidental,
so the FI suite and Phase 2 pipeline tests stay green unchanged whether
or not this module is ever imported.
"""
from __future__ import annotations

import functools
import os
import sqlite3
from typing import Callable

from contracts.schemas import CheckTask

CHECKER_MODE_ENV = "CHECKER_MODE"


def get_checker_fn(
    conn: sqlite3.Connection | None = None,
    run_id: str = "run",
    mode: str | None = None,
) -> Callable[[CheckTask], list[dict]]:
    """mode, if given, overrides the CHECKER_MODE env var, which itself
    defaults to "stub". mode="real" requires a ledger connection.
    """
    mode = mode or os.environ.get(CHECKER_MODE_ENV, "stub")
    if mode == "real":
        if conn is None:
            raise ValueError("real checker requires a ledger connection")
        from .harness import real_checker

        return functools.partial(real_checker, ledger_conn=conn, run_id=run_id)
    if mode != "stub":
        raise ValueError(f"unknown CHECKER_MODE {mode!r}, expected 'stub' or 'real'")
    from .stub import stub_checker

    return stub_checker
