"""
Confirms every gate in audit/fidelity.py produces identical results when
run twice against the same database. Runs against the small 1,000-person
fixture (data/claims_ci.duckdb) rather than the full file, so this stays
fast enough for CI.

If this test fails for a gate, that gate has an ordering or randomization
dependency that isn't properly seeded/sorted — find it before trusting
that gate's numbers.
"""

import duckdb
import pytest

from audit.fidelity import (
    gate1_refill_pairs,
    gate2_labeler_concentration_null,
    gate3_90day_share_null,
    gate4_monthly_plateau_threshold,
    gate6_test1_days_supply_timing,
    gate6_test2_timing_structure,
    gate6_test3_file_connectivity,
    part_d_corrections,
)
from audit.gate7_terminal_stop import (
    gate7_decision,
    load_gate7_population,
    run_gate7_bands,
)

FIXTURE_DB = "data/claims_ci.duckdb"


@pytest.fixture(scope="module")
def con():
    connection = duckdb.connect(FIXTURE_DB, read_only=True)
    yield connection
    connection.close()


def test_gate1_deterministic(con):
    assert gate1_refill_pairs(con) == gate1_refill_pairs(con)


def test_gate2_deterministic(con):
    assert gate2_labeler_concentration_null(con) == pytest.approx(
        gate2_labeler_concentration_null(con)
    )


def test_gate3_deterministic(con):
    assert gate3_90day_share_null(con) == pytest.approx(gate3_90day_share_null(con))


def test_gate4_deterministic(con):
    assert gate4_monthly_plateau_threshold(con) == gate4_monthly_plateau_threshold(con)


def test_gate6_test1_deterministic(con):
    result_a, _ = gate6_test1_days_supply_timing(con)
    result_b, _ = gate6_test1_days_supply_timing(con)
    assert result_a == result_b


def test_gate6_test2_deterministic(con):
    _, clean_pde = gate6_test1_days_supply_timing(con)
    result_a = gate6_test2_timing_structure(clean_pde)
    result_b = gate6_test2_timing_structure(clean_pde)
    assert result_a == result_b


def test_gate6_test3_deterministic(con):
    assert gate6_test3_file_connectivity(con) == pytest.approx(gate6_test3_file_connectivity(con))


def test_part_d_corrections_deterministic(con):
    assert part_d_corrections(con) == pytest.approx(part_d_corrections(con))


def test_gate7_population_deterministic(con):
    assert load_gate7_population(con).to_dicts() == load_gate7_population(con).to_dicts()


def test_gate7_decision_deterministic(con):
    pop_a, shares_a = run_gate7_bands(con, n_redraws=3)
    pop_b, shares_b = run_gate7_bands(con, n_redraws=3)
    decision_a = gate7_decision(pop_a, shares_a)
    decision_b = gate7_decision(pop_b, shares_b)
    assert decision_a == pytest.approx(decision_b)
