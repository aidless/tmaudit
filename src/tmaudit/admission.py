"""tmaudit.admission — statistical admission certificates for self-evolving
harness claims.

Motivation
----------
A growing class of papers reports that an agent's *harness* (prompts, tools,
memory, middleware, control logic) was revised by an automated loop while the
model weights were held fixed, and cites a benchmark delta as evidence that the
revision "worked". Selection on empirical fitness does not by itself establish
generalization: each accepted revision was chosen against the same evidence that
is later reported as the result.

``arXiv:2610.18813`` (Self-evolving Agent Harness, §4.2) states a sufficient
condition for admitting a revision, using a fresh, independent validation set:

    Δ_k(H') ≤ Δ̂_k(H') + sqrt( 2 ln(KT/δ) / m )          (eq. 8, p.7)

    "Accept only candidates with negative upper bounds."

and, for the case where evaluator-defined loss may differ from the target risk
by at most η:

    Δ̂_k(H') + sqrt( 2*ln(KT/δ) / m ) + 2η < 0            (eq. 9, p.8)

where Δ is a *loss* difference, so a positive improvement corresponds to a
negative Δ. ``m`` is the number of fresh independent **tasks** — the source is
explicit that extra rollouts raise precision without raising the sample size
(p.7, "Scope of the guarantees").

This module implements those two inequalities plus the retention bookkeeping of
eq. (6), so that a reported gain can be labelled *certified* or *uncertified*
against a stated sample size, and so that the sample size required for a claimed
gain can be inverted.

Design constraints
------------------
* **Stdlib only.** ``pyproject.toml`` declares ``dependencies = []`` and that is
  a property of this package; nothing here imports outside the standard library.
* **No silent defaults in the CLI.** K, T, delta and eta all change the verdict,
  so the command reports the full parameter set and echoes it back in JSON.
* **Pure functions.** The math helpers are importable without constructing a
  config, which is what the tests exercise.

Caveats that belong to the method, not the implementation
---------------------------------------------------------
* The bound holds for the *historical mixture* of tasks, not for an arbitrary
  future distribution.
* η must be backed by external evidence (executable checks or independent human
  assessment); without it the certificate covers evaluator-defined loss only.
* The function certifies a *gain*, not a *cause*. A certified delta still says
  nothing about which component produced it.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

__all__ = [
    "Verdict",
    "RetentionLedger",
    "slack",
    "margin",
    "certify",
    "required_tasks",
    "retention_ledger",
    "sweep",
    "parse_claims",
    "audit_claims",
]

#: 2 * ln(KT/delta) for practically never needs more than this range of m.
_MAX_TASKS = sys.maxsize


# ---------------------------------------------------------------------------
# Core inequalities
# ---------------------------------------------------------------------------
def slack(candidates: int, rounds: int, delta: float) -> float:
    """Return ``2 * ln(K * T / delta)``, the numerator inside the sqrt.

    Parameters
    ----------
    candidates : K
        Upper bound on the number of candidates compared per round.
    rounds : T
        Total number of comparison rounds covered by the union bound.
    delta : float
        Failure probability budget for the whole campaign.

    Raises
    ------
    ValueError
        If ``candidates`` or ``rounds`` is below 1, or ``delta`` is outside
        ``(0, 1)``.
    """
    if candidates < 1:
        raise ValueError(f"candidates must be >= 1, got {candidates!r}")
    if rounds < 1:
        raise ValueError(f"rounds must be >= 1, got {rounds!r}")
    if not 0.0 < delta < 1.0:
        raise ValueError(f"delta must be in (0, 1), got {delta!r}")
    return 2.0 * math.log(candidates * rounds / delta)


def margin(tasks: int, candidates: int, rounds: int, delta: float) -> float:
    """Confidence half-width of the paired loss difference, as a fraction.

    Multiply by 100 to express it in percentage points.
    """
    if tasks < 2:
        raise ValueError(f"tasks must be >= 2 for a paired sample, got {tasks!r}")
    return math.sqrt(slack(candidates, rounds, delta) / tasks)


@dataclass(frozen=True)
class Verdict:
    """Outcome of applying eq. (8)/(9) to one reported gain."""

    gain_pp: float
    tasks: int
    candidates: int
    rounds: int
    delta: float
    eta_pp: float
    upper_pp: float
    certified: bool
    required_gain_pp: float

    def as_row(self) -> str:
        tag = "CERTIFIED" if self.certified else "NOT CERTIFIED"
        return (
            f"[{tag}] gain={self.gain_pp:+.2f}pp  "
            f"upper={self.upper_pp:+.2f}pp  "
            f"m={self.tasks:,}  K={self.candidates}  T={self.rounds}  "
            f"delta={self.delta}  eta={self.eta_pp:.2f}pp"
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def certify(
    gain_pp: float,
    tasks: int,
    candidates: int = 5,
    rounds: int = 10,
    delta: float = 0.05,
    eta_pp: float = 0.0,
) -> Verdict:
    """Apply the admission rule to one reported gain, in percentage points.

    The gain is supplied with a positive sign for an improvement. Internally it
    is converted to a loss difference (``Delta_hat = -gain``), so the reported
    ``upper_pp`` is the upper confidence bound on Δ and the candidate is
    admitted exactly when that bound is negative.

    Parameters
    ----------
    gain_pp : float
        Observed paired improvement on the fresh validation set, in pp.
    tasks : int
        Number of fresh, independent **tasks** in the validation set (``m``).
    candidates : int
        Max candidates compared per round (``K``, default 5).
    rounds : int
        Number of rounds covered by the union bound (``T``, default 10).
    delta : float
        Failure probability budget (default 0.05).
    eta_pp : float
        Upper bound on the gap between evaluator loss and target risk, in pp.

    Returns
    -------
    Verdict
    """
    half_width_pp = margin(tasks, candidates, rounds, delta) * 100.0
    # eq. (8) is stated on Delta = -gain, so the upper confidence bound is
    #   Delta_hat + half_width = -gain + half_width = half_width - gain,
    # and the candidate is admitted exactly when that bound is negative --
    # i.e. when the gain exceeds the half-width. At gain == half_width the
    # bound is 0, which is not < 0, so the boundary is not certified.
    upper_pp = half_width_pp - gain_pp + 2.0 * eta_pp
    return Verdict(
        gain_pp=float(gain_pp),
        tasks=int(tasks),
        candidates=int(candidates),
        rounds=int(rounds),
        delta=float(delta),
        eta_pp=float(eta_pp),
        upper_pp=upper_pp,
        certified=upper_pp < 0.0,
        required_gain_pp=half_width_pp + 2.0 * eta_pp,
    )


def required_tasks(
    gain_pp: float,
    candidates: int = 5,
    rounds: int = 10,
    delta: float = 0.05,
    eta_pp: float = 0.0,
) -> int:
    """Invert eq. (8): how many fresh tasks are needed to certify ``gain_pp``.

    Returns ``sys.maxsize`` when the evaluator-gap allowance ``2*eta_pp``
    already consumes the whole gain, i.e. no sample size can certify it.

    Raises
    ------
    ValueError
        If ``gain_pp`` is not positive. Negative gains are rejected by
        construction and need no certificate.
    """
    if gain_pp <= 0:
        raise ValueError(f"gain_pp must be positive, got {gain_pp!r}")
    budget = (gain_pp - 2.0 * eta_pp) / 100.0
    if budget <= 0:
        return _MAX_TASKS
    return math.ceil(slack(candidates, rounds, delta) / (budget ** 2))


# ---------------------------------------------------------------------------
# Retention bookkeeping (eq. 6)
# ---------------------------------------------------------------------------
@dataclass
class RetentionLedger:
    """Retention bound bookkeeping from eq. (6).

    ``ERs(H_k) <= ER_hat_s(H_s) + beta_s,s + sum(eps_{s,u})``

    The ``eps`` terms are *separate assumptions* that accumulate (p.7), not
    consequences of stability. Once their sum reaches the gain being defended,
    the bound is vacuous: it permits the model to lose everything that was won.
    """

    eps_pp: list[float]
    gain_pp: float
    beta_ss_pp: float = 0.0

    @property
    def rounds(self) -> int:
        return len(self.eps_pp)

    @property
    def sum_eps_pp(self) -> float:
        return float(sum(self.eps_pp))

    @property
    def residual_pp(self) -> float:
        """Gain left after the accumulated regression allowance and beta."""
        return self.gain_pp - self.sum_eps_pp - self.beta_ss_pp

    @property
    def vacuous(self) -> bool:
        """True when the retained gain cannot be distinguished from zero."""
        return self.residual_pp <= 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rounds": self.rounds,
            "gain_pp": round(self.gain_pp, 3),
            "beta_ss_pp": round(self.beta_ss_pp, 3),
            "sum_eps_pp": round(self.sum_eps_pp, 3),
            "mean_eps_pp": round(self.sum_eps_pp / self.rounds, 3)
            if self.rounds
            else 0.0,
            "residual_pp": round(self.residual_pp, 3),
            "vacuous": self.vacuous,
        }


def retention_ledger(
    eps_pp: Iterable[float],
    gain_pp: float,
    beta_ss_pp: float = 0.0,
) -> RetentionLedger:
    """Build a :class:`RetentionLedger` from per-round regression allowances."""
    return RetentionLedger(
        eps_pp=[float(e) for e in eps_pp],
        gain_pp=float(gain_pp),
        beta_ss_pp=float(beta_ss_pp),
    )


def sweep(
    candidates: int = 5,
    rounds: int = 10,
    delta: float = 0.05,
    eta_pp: float = 0.0,
    sizes: Sequence[int] = (89, 200, 500, 1000, 2000, 5000, 10000, 20000),
) -> list[tuple[int, float]]:
    """Return ``(m, minimum certifiable gain in pp)`` pairs for a size grid."""
    return [
        (int(m), margin(int(m), candidates, rounds, delta) * 100.0 + 2.0 * eta_pp)
        for m in sizes
    ]


# ---------------------------------------------------------------------------
# Batch audit over a claims file
# ---------------------------------------------------------------------------
_CLAIM_REQUIRED = ("name", "gain_pp", "tasks")


def parse_claims(path: Path) -> list[dict[str, Any]]:
    """Load and validate a claims JSON file.

    Schema::

        [
          {"name": "...", "gain_pp": 7.3, "tasks": 89,
           "candidates": 5, "rounds": 10, "delta": 0.05, "eta_pp": 0.0}
        ]

    Only ``name``, ``gain_pp`` and ``tasks`` are required; the rest fall back to
    :func:`certify` defaults so that a minimal file is still auditable.

    Raises
    ------
    ValueError
        If the payload is not a list of objects, or an entry is missing a
        required key, or a numeric field is of the wrong type.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        if "claims" not in raw:
            raise ValueError(
                "claims file is an object without a 'claims' key; expected "
                "either a list of claim objects or {\"claims\": [...]}"
            )
        raw = raw["claims"]
    if not isinstance(raw, list):
        raise ValueError("claims file must contain a list of claim objects")
    claims: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"claim #{i} is not an object")
        missing = [k for k in _CLAIM_REQUIRED if k not in item]
        if missing:
            raise ValueError(f"claim #{i} ({item.get('name', '?')}) missing {missing}")
        for key in ("gain_pp", "eta_pp"):
            if key in item and not isinstance(item[key], (int, float)):
                raise ValueError(f"claim #{i} field {key!r} must be numeric")
        if not isinstance(item["tasks"], int) or item["tasks"] < 2:
            raise ValueError(f"claim #{i} field 'tasks' must be an int >= 2")
        claims.append(item)
    return claims


def audit_claims(
    claims: Sequence[dict[str, Any]],
) -> list[tuple[dict[str, Any], Verdict, int]]:
    """Certify every claim; return ``(claim, verdict, required_tasks)`` triples."""
    out: list[tuple[dict[str, Any], Verdict, int]] = []
    for c in claims:
        v = certify(
            float(c["gain_pp"]),
            int(c["tasks"]),
            int(c.get("candidates", 5)),
            int(c.get("rounds", 10)),
            float(c.get("delta", 0.05)),
            float(c.get("eta_pp", 0.0)),
        )
        need = required_tasks(
            max(v.gain_pp, 1e-9),
            v.candidates,
            v.rounds,
            v.delta,
            v.eta_pp,
        )
        out.append((c, v, need))
    return out


# ---------------------------------------------------------------------------
# CLI handler (wired into tmaudit.cli)
# ---------------------------------------------------------------------------
def _render_table(rows: Sequence[tuple[dict[str, Any], Verdict, int]]) -> None:
    name_w = max([len(c.get("name", "?")) for c, _, _ in rows] + [12])
    name_w = min(name_w, 46)
    print(
        f"{'claim':<{name_w}}  {'gain':>9}  {'m':>8}  {'needed_m':>10}  verdict"
    )
    print("-" * (name_w + 48))
    for c, v, need in rows:
        need_s = "infeasible" if need == _MAX_TASKS else f"{need:,}"
        verdict = "PASS" if v.certified else "FAIL"
        print(
            f"{c.get('name', '?')[:name_w]:<{name_w}}  "
            f"{v.gain_pp:+8.2f}pp  {v.tasks:>8,}  {need_s:>10}  {verdict}"
        )
    print("-" * (name_w + 48))
    fails = sum(1 for _, v, _ in rows if not v.certified)
    print(f"{len(rows)} claim(s), {fails} uncertified")


def cmd_admission(args) -> int:
    """``tmaudit admission ...`` — see :mod:`tmaudit.cli` for the flags."""
    try:
        if getattr(args, "audit", None):
            claims = parse_claims(Path(args.audit))
            rows = audit_claims(claims)
            _render_table(rows)
            if getattr(args, "json", False):
                print()
                print(
                    json.dumps(
                        [
                            {**v.to_dict(), "name": c.get("name"), "needed_m_tasks": n}
                            for c, v, n in rows
                        ],
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            return 1 if any(not v.certified for _, v, _ in rows) else 0

        if getattr(args, "grid", False):
            print(
                f"| tasks m | minimum certifiable gain "
                f"(K={args.candidates}, T={args.rounds}, delta={args.delta}) |"
            )
            print("|---|---|")
            for m, gain in sweep(
                args.candidates,
                args.rounds,
                args.delta,
                args.eta_pp,
                sizes=args.sizes,
            ):
                print(f"| {m:,} | {gain:.1f} pp |")
            return 0

        if getattr(args, "required_tasks", None) is not None:
            need = required_tasks(
                args.required_tasks,
                args.candidates,
                args.rounds,
                args.delta,
                args.eta_pp,
            )
            if need == _MAX_TASKS:
                print("infeasible: eta allowance consumes the whole gain")
                return 1
            print(f"tasks m >= {need:,}")
            return 0

        if getattr(args, "gain", None) is None or getattr(args, "tasks", None) is None:
            print(
                "tmaudit admission: need either --audit FILE, --grid, "
                "--required-tasks GAIN_PP, or both --gain and --tasks",
                file=sys.stderr,
            )
            return 2

        verdict = certify(
            args.gain,
            args.tasks,
            args.candidates,
            args.rounds,
            args.delta,
            args.eta_pp,
        )
        print(verdict.as_row())
        if not verdict.certified:
            need = required_tasks(
                max(verdict.gain_pp, 1e-9),
                verdict.candidates,
                verdict.rounds,
                verdict.delta,
                verdict.eta_pp,
            )
            if need == _MAX_TASKS:
                print("note: eta allowance consumes the whole gain; no m suffices")
            else:
                print(f"note: certifying this gain would need tasks m >= {need:,}")
        if getattr(args, "json", False):
            print(json.dumps(verdict.to_dict(), ensure_ascii=False, indent=2))
        return 0 if verdict.certified else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"tmaudit admission: {exc}", file=sys.stderr)
        return 2
