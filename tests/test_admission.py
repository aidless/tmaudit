"""Tests for the statistical admission rule in ``tmaudit.admission``.

The reference values below are computed by hand from arXiv:2610.18813 eq. (8):

    Delta_hat + sqrt( 2 * ln(K*T/delta) / m ) < 0

so each assertion pins a number a reviewer can re-derive with a calculator
rather than a value captured from a previous run of this module.

Also covers the CLI wiring, because ``tmaudit admission`` is the only way the
rule reaches a user.
"""
from __future__ import annotations

import json
import math
import sys

import pytest

from tmaudit import admission as A


# ---------------------------------------------------------------------------
# eq. (8) numerator
# ---------------------------------------------------------------------------
def test_slack_matches_hand_calculation():
    # 2*ln(5*50/0.05) = 2*ln(5000) = 17.0344
    assert A.slack(5, 50, 0.05) == pytest.approx(17.0344, abs=1e-4)


def test_slack_defaults_k5_t10():
    # 2*ln(5*10/0.05) = 2*ln(1000) = 13.8155
    assert A.slack(5, 10, 0.05) == pytest.approx(13.8155, abs=1e-4)


@pytest.mark.parametrize(
    "K,T,delta",
    [(0, 10, 0.05), (5, 0, 0.05), (5, 10, 0.0), (5, 10, 1.0), (5, 10, -0.1)],
)
def test_slack_rejects_degenerate_arguments(K, T, delta):
    with pytest.raises(ValueError):
        A.slack(K, T, delta)


def test_margin_requires_paired_sample():
    with pytest.raises(ValueError):
        A.margin(1, 5, 10, 0.05)


# ---------------------------------------------------------------------------
# certify: the two-sided behaviour that makes the rule a filter, not a rubber stamp
# ---------------------------------------------------------------------------
def test_small_gain_on_small_benchmark_is_not_certified():
    # sqrt(13.8155/89) = 0.394 -> 39.4pp half-width > 7.3pp gain
    v = A.certify(gain_pp=7.3, tasks=89)
    assert v.certified is False
    assert v.upper_pp == pytest.approx(32.10, abs=0.02)
    assert v.required_gain_pp == pytest.approx(39.40, abs=0.02)


def test_large_gain_on_small_benchmark_is_certified():
    v = A.certify(gain_pp=45.0, tasks=89)
    assert v.certified is True
    assert v.upper_pp < 0


def test_negative_gain_is_never_certified():
    v = A.certify(gain_pp=-3.0, tasks=2000)
    assert v.certified is False
    assert v.upper_pp > 0


def test_more_tasks_narrows_the_bound():
    narrow = A.certify(gain_pp=7.3, tasks=2000)
    wide = A.certify(gain_pp=7.3, tasks=89)
    assert narrow.upper_pp < wide.upper_pp


def test_evaluator_gap_consumes_the_certificate():
    # 2*eta = 4pp must be added to the required gain. At m=2000 the clean
    # half-width is 8.31pp, so a 9pp gain certifies and a 2pp evaluator gap
    # (total requirement 12.31pp) kills it.
    clean = A.certify(gain_pp=9.0, tasks=2000, eta_pp=0.0)
    biased = A.certify(gain_pp=9.0, tasks=2000, eta_pp=2.0)
    assert biased.upper_pp - clean.upper_pp == pytest.approx(4.0, abs=1e-9)
    assert clean.certified is True
    assert biased.certified is False


def test_verdict_serialises_to_json_safe_dict():
    v = A.certify(gain_pp=7.3, tasks=89)
    payload = json.loads(json.dumps(v.to_dict()))
    assert payload["tasks"] == 89
    assert payload["certified"] is False
    assert "upper_pp" in payload


# ---------------------------------------------------------------------------
# required_tasks: the inversion
# ---------------------------------------------------------------------------
def test_required_tasks_two_points_matches_closed_form():
    # ceil(2*ln(5*50/0.05) / 0.02**2) = ceil(17.0344/0.0004) = 42586
    assert A.required_tasks(2.0, candidates=5, rounds=50) == 42586


def test_required_tasks_matches_default_case():
    # ceil(13.8155 / 0.073**2) = 2593
    assert A.required_tasks(7.3) == 2593


def test_required_tasks_infeasible_when_eta_exceeds_gain():
    assert A.required_tasks(7.3, eta_pp=4.0) == sys.maxsize


def test_required_tasks_rejects_non_positive_gain():
    with pytest.raises(ValueError):
        A.required_tasks(0.0)
    with pytest.raises(ValueError):
        A.required_tasks(-1.0)


@pytest.mark.parametrize("gain", [3.0, 5.0, 11.0, 20.0])
def test_required_tasks_round_trips_with_certify(gain):
    """The m returned by required_tasks must be enough to certify the gain."""
    m = A.required_tasks(gain)
    assert A.certify(gain_pp=gain, tasks=m).certified is True
    # ...and one task fewer must not be enough.
    assert A.certify(gain_pp=gain, tasks=m - 1).certified is False


# ---------------------------------------------------------------------------
# eq. (6): retention bookkeeping
# ---------------------------------------------------------------------------
def test_retention_ledger_vacuous_once_eps_consumes_gain():
    led = A.retention_ledger([1.0] * 10, gain_pp=7.3)
    assert led.rounds == 10
    assert led.sum_eps_pp == pytest.approx(10.0)
    assert led.vacuous is True
    assert led.residual_pp == pytest.approx(-2.7)


def test_retention_ledger_beta_counts_against_the_gain():
    led = A.retention_ledger([0.2] * 5, gain_pp=7.3, beta_ss_pp=6.0)
    # 7.3 - 1.0 - 6.0 = 0.3 -> still non-vacuous
    assert led.vacuous is False
    assert led.residual_pp == pytest.approx(0.3)
    # raising beta by 0.5 tips it over
    led2 = A.retention_ledger([0.2] * 5, gain_pp=7.3, beta_ss_pp=6.5)
    assert led2.vacuous is True


def test_retention_ledger_handles_empty_eps():
    led = A.retention_ledger([], gain_pp=5.0)
    d = led.to_dict()
    assert d["rounds"] == 0
    assert d["mean_eps_pp"] == 0.0
    assert led.vacuous is False


# ---------------------------------------------------------------------------
# claims file parsing / auditing
# ---------------------------------------------------------------------------
def _write(tmp_path, payload):
    p = tmp_path / "claims.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_parse_claims_accepts_minimal_entries(tmp_path):
    p = _write(tmp_path, [{"name": "x", "gain_pp": 7.3, "tasks": 89}])
    claims = A.parse_claims(p)
    assert claims[0]["name"] == "x"


def test_parse_claims_accepts_top_level_dict(tmp_path):
    p = _write(tmp_path, {"claims": [{"name": "x", "gain_pp": 1.0, "tasks": 10}]})
    assert len(A.parse_claims(p)) == 1


def test_parse_claims_rejects_missing_key(tmp_path):
    p = _write(tmp_path, [{"name": "x", "gain_pp": 7.3}])
    with pytest.raises(ValueError, match="missing"):
        A.parse_claims(p)


def test_parse_claims_rejects_non_integer_tasks(tmp_path):
    p = _write(tmp_path, [{"name": "x", "gain_pp": 7.3, "tasks": 89.5}])
    with pytest.raises(ValueError, match="tasks"):
        A.parse_claims(p)


def test_parse_claims_rejects_non_numeric_gain(tmp_path):
    p = _write(tmp_path, [{"name": "x", "gain_pp": "7.3", "tasks": 89}])
    with pytest.raises(ValueError, match="numeric"):
        A.parse_claims(p)


def test_parse_claims_rejects_non_list(tmp_path):
    p = _write(tmp_path, {"nope": 1})
    with pytest.raises(ValueError):
        A.parse_claims(p)


def test_audit_claims_reports_required_tasks(tmp_path):
    p = _write(
        tmp_path,
        [
            {"name": "big", "gain_pp": 45.0, "tasks": 89},
            {"name": "small", "gain_pp": 7.3, "tasks": 89},
        ],
    )
    rows = A.audit_claims(A.parse_claims(p))
    by_name = {c["name"]: (v, n) for c, v, n in rows}
    assert by_name["big"][0].certified is True
    assert by_name["small"][0].certified is False
    assert by_name["small"][1] == 2593


# ---------------------------------------------------------------------------
# grid helper
# ---------------------------------------------------------------------------
def test_sweep_is_monotonically_decreasing_in_m():
    rows = A.sweep(sizes=(89, 500, 2000, 5000))
    gains = [g for _, g in rows]
    assert gains == sorted(gains, reverse=True)
    assert rows[0][0] == 89
    assert rows[0][1] == pytest.approx(39.40, abs=0.02)


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------
def _run(argv):
    from tmaudit.cli import main

    return main(argv)


def test_cli_single_gain_not_certified_exits_1(capsys):
    rc = _run(["admission", "--gain", "7.3", "--tasks", "89"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "NOT CERTIFIED" in out
    assert "2,593" in out


def test_cli_single_gain_certified_exits_0(capsys):
    rc = _run(["admission", "--gain", "45", "--tasks", "89"])
    assert rc == 0
    assert "CERTIFIED" in capsys.readouterr().out


def test_cli_json_output_is_parseable(capsys):
    _run(["admission", "--gain", "7.3", "--tasks", "89", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out[out.index("{"):])
    assert payload["tasks"] == 89
    assert math.isclose(payload["upper_pp"], 32.10, abs_tol=0.02)


def test_cli_required_tasks(capsys):
    rc = _run(["admission", "--required-tasks", "7.3"])
    assert rc == 0
    assert "2,593" in capsys.readouterr().out


def test_cli_grid(capsys):
    rc = _run(["admission", "--grid", "--sizes", "89", "2000"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "39.4 pp" in out and "8.3 pp" in out


def test_cli_missing_arguments_exits_2(capsys):
    rc = _run(["admission"])
    assert rc == 2
    assert "need either" in capsys.readouterr().err


def test_cli_audit_file(tmp_path, capsys):
    p = _write(tmp_path, [{"name": "small", "gain_pp": 7.3, "tasks": 89}])
    rc = _run(["admission", "--audit", str(p)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "small" in out
    assert "1 claim(s), 1 uncertified" in out


def test_cli_bad_audit_file_returns_2(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    rc = _run(["admission", "--audit", str(bad)])
    assert rc == 2
    assert "tmaudit admission:" in capsys.readouterr().err
