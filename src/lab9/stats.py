"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
import math

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError("human and judge labels must have the same length")
    tp = fp = fn = tn = 0
    for actual, predicted in zip(human, judge):
        actual = _normalize_label(actual)
        predicted = _normalize_label(predicted)
        actual_fail, predicted_fail = actual == POS, predicted == POS
        if actual_fail and predicted_fail:
            tp += 1
        elif predicted_fail:
            fp += 1
        elif actual_fail:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def _normalize_label(label: str) -> str:
    if not isinstance(label, str):
        raise ValueError("judge labels must be PASS or FAIL")
    normalized = label.strip().upper()
    if normalized not in {"PASS", POS}:
        raise ValueError(f"unknown judge label: {label!r}")
    return normalized


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    predicted_positive = cm["tp"] + cm["fp"]
    actual_positive = cm["tp"] + cm["fn"]
    precision = cm["tp"] / predicted_positive if predicted_positive else 0.0
    recall = cm["tp"] / actual_positive if actual_positive else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    if len(human) != len(judge):
        raise ValueError("human and judge labels must have the same length")
    if len(human) == 0:
        raise ValueError("kappa is undefined for empty labels")
    cm = confusion(human, judge)
    n = len(human)
    observed = (cm["tp"] + cm["tn"]) / n
    human_fail = (cm["tp"] + cm["fn"]) / n
    judge_fail = (cm["tp"] + cm["fp"]) / n
    expected = human_fail * judge_fail + (1 - human_fail) * (1 - judge_fail)
    if math.isclose(expected, 1.0):
        raise ValueError("kappa is undefined when expected agreement is 1")
    return (observed - expected) / (1 - expected)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    values = (observed_rate, sensitivity, specificity)
    if any(not math.isfinite(x) or not 0 <= x <= 1 for x in values):
        raise ValueError("observed rate, sensitivity, and specificity must be in [0, 1]")
    denominator = sensitivity + specificity - 1
    if math.isclose(denominator, 0.0):
        raise ValueError("Rogan-Gladen correction is undefined when sensitivity + specificity = 1")
    return min(1.0, max(0.0, (observed_rate + specificity - 1) / denominator))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    if len(a) != len(b):
        raise ValueError("paired samples must have the same length")
    if len(a) == 0:
        raise ValueError("paired bootstrap requires at least one observation")
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, int) or n_resamples <= 0:
        raise ValueError("n_resamples must be positive")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    if any(not math.isfinite(float(x)) for x in (*a, *b)):
        raise ValueError("paired samples must contain only finite values")
    if all(x == y for x, y in zip(a, b)):
        return 0.0, 0.0, 0.0

    import numpy as np
    from scipy.stats import bootstrap

    result = bootstrap(
        (np.asarray(a, dtype=float), np.asarray(b, dtype=float)),
        lambda x, y, axis: np.mean(x - y, axis=axis),
        paired=True,
        vectorized=True,
        n_resamples=n_resamples,
        confidence_level=confidence,
        method="percentile",
        rng=np.random.default_rng(rng),
    )
    return float(np.mean(np.asarray(a, dtype=float) - np.asarray(b, dtype=float))), \
        float(result.confidence_interval.low), float(result.confidence_interval.high)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_pass_k(n, c, k)
    if k > n - c:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_pass_k(n, c, k)
    if k > c:
        return 0.0
    return math.comb(c, k) / math.comb(n, k)


def _validate_pass_k(n: int, c: int, k: int) -> None:
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (n, c, k)):
        raise ValueError("n, c, and k must be integers")
    if n <= 0 or not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("require n > 0, 0 <= c <= n, and 1 <= k <= n")
