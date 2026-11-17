"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems: list[str] = []
    if not isinstance(pr.get("manifest"), dict):
        problems.append("missing report manifest")
    if not isinstance(pr.get("rows"), list):
        problems.append("missing report rows")
    if not isinstance(pr.get("metrics"), dict):
        problems.append("missing report metrics")
    rows = pr.get("rows")
    if not isinstance(rows, list):
        rows = []
    base_rows = base.get("rows")
    if not isinstance(base_rows, list):
        problems.append("baseline report rows are missing")
        base_rows = []
    manifest = pr.get("manifest")
    if not isinstance(manifest, dict):
        manifest = {}
    metrics = pr.get("metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    seeds = manifest.get("seeds")
    if not isinstance(seeds, list) or any(
        isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds
    ):
        problems.append("manifest seeds must be a list of integers")
        seeds = []
    item_count = manifest.get("items")
    if isinstance(item_count, bool) or not isinstance(item_count, int) or item_count < 0:
        problems.append("manifest items must be a non-negative integer")
        item_count = 0
    if "metric_spec" in pr and pr["metric_spec"] != spec:
        problems.append("report metric_spec differs from gate spec")
    if manifest.get("eval_set_version") not in (None, spec.get("eval_set_version")):
        problems.append("report eval_set_version differs from gate spec")
    if manifest.get("metric_spec_version") not in (None, spec.get("metric_spec_version")):
        problems.append("report metric_spec_version differs from gate spec")
    expected_rows = item_count * len(seeds)
    if len(rows) != expected_rows:
        problems.append(f"row count {len(rows)} != manifest items × seeds ({expected_rows})")

    def row_keys(values: list[dict]) -> list[tuple[str, str]]:
        result = []
        for row in values:
            if not isinstance(row, dict):
                result.append((repr(row), repr(row)))
                continue
            item_id, seed = row.get("item_id"), row.get("seed")
            if not isinstance(item_id, str) or isinstance(seed, bool) or not isinstance(seed, int):
                problems.append("row has invalid item_id or seed")
                result.append((repr(item_id), repr(seed)))
            else:
                result.append((item_id, str(seed)))
        return result

    keys = row_keys(rows)
    base_keys = row_keys(base_rows)
    if any(not isinstance(row, dict) for row in rows):
        problems.append("report contains a non-object row")
    if len(set(keys)) != len(keys):
        problems.append("duplicate (item_id, seed) rows")
    if set(keys) != set(base_keys):
        problems.append("(item_id, seed) set differs from baseline")
    if len({key[0] for key in keys}) != item_count:
        problems.append("unique item count differs from manifest")
    row_seeds = [r.get("seed") for r in rows if isinstance(r, dict)]
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in row_seeds):
        problems.append("row contains an invalid seed")
    if {seed for seed in row_seeds if isinstance(seed, int) and not isinstance(seed, bool)} != set(seeds):
        problems.append("row seed set differs from manifest")

    for metric, value in metrics.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool) and not math.isfinite(value):
            problems.append(f"metric {metric} is not finite")
    for metric in (m["id"] for m in spec.get("metrics", []) if m["id"] in GRADERS):
        missing_rows = [r for r in rows if not isinstance(r, dict) or metric not in r or r[metric] is None]
        if missing_rows:
            problems.append(f"graded metric {metric} missing/None on {len(missing_rows)} row(s)")

    if pr.get("evaluator_failures"):
        problems.append(f"{len(pr['evaluator_failures'])} evaluator failure(s)")

    base_by_key = {key: row for key, row in zip(base_keys, base_rows)}
    for key, row in zip(keys, rows):
        base_row = base_by_key.get(key)
        if base_row is not None:
            row_slices = row.get("slices") if isinstance(row, dict) else None
            base_slices = base_row.get("slices") if isinstance(base_row, dict) else None
            if (not isinstance(row_slices, list) or not isinstance(base_slices, list)
                    or any(not isinstance(tag, str) for tag in (*row_slices, *base_slices))
                    or set(row_slices) != set(base_slices)):
                problems.append(f"slice tags differ from baseline for {key[0]}@{key[1]}")
                break

    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        prior_metrics = {m["id"]: m for m in base_spec.get("metrics", [])}
        current_metrics = {m["id"]: m for m in spec.get("metrics", [])}
        for mid, prior in prior_metrics.items():
            current = current_metrics.get(mid)
            if current is None:
                problems.append(f"ratchet: metric {mid} disappeared")
                continue
            old_threshold = prior.get("threshold") or {}
            new_threshold = current.get("threshold") or {}
            for direction in ("min", "max"):
                if direction in old_threshold and (
                    direction not in new_threshold
                    or (direction == "min" and new_threshold[direction] < old_threshold[direction])
                    or (direction == "max" and new_threshold[direction] > old_threshold[direction])
                ):
                    problems.append(f"ratchet: metric {mid} loosened {direction} threshold")
            if prior.get("blocking") and not current.get("blocking"):
                problems.append(f"ratchet: metric {mid} became non-blocking")
            if old_threshold.get("no_significant_drop") and not new_threshold.get("no_significant_drop"):
                problems.append(f"ratchet: metric {mid} dropped no_significant_drop")

        prior_slices = {s["name"]: s for s in base_spec.get("slices", [])}
        current_slices = {s["name"]: s for s in spec.get("slices", [])}
        for name, prior in prior_slices.items():
            current = current_slices.get(name)
            if current is None:
                problems.append(f"ratchet: slice {name} disappeared")
                continue
            if "min" in prior and ("min" not in current or current["min"] < prior["min"]):
                problems.append(f"ratchet: slice {name} loosened min threshold")
            if "max" in prior and ("max" not in current or current["max"] > prior["max"]):
                problems.append(f"ratchet: slice {name} loosened max threshold")
            if prior.get("blocking") and not current.get("blocking"):
                problems.append(f"ratchet: slice {name} became non-blocking")
            if prior.get("no_significant_drop") and not current.get("no_significant_drop"):
                problems.append(f"ratchet: slice {name} dropped no_significant_drop")
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bootstrap = spec.get("bootstrap", {})
    for item in spec.get("slices", []):
        name, metric = item["name"], item["metric"]
        current = per_item(pr, metric, slice_name=name)
        baseline = per_item(base, metric, slice_name=name)
        keys = sorted(set(current) & set(baseline))
        value = sum(current.values()) / len(current) if current else None
        threshold = {k: item[k] for k in ("min", "max", "no_significant_drop") if k in item}
        verdict = "ok"
        note = ""
        if not current or not keys:
            verdict = "missing"
        else:
            if "min" in item and value < item["min"]:
                verdict = "fail"
            if "max" in item and value > item["max"]:
                verdict = "fail"
            if item.get("no_significant_drop"):
                delta, lo, hi = stats.paired_bootstrap(
                    [current[k] for k in keys], [baseline[k] for k in keys],
                    n_resamples=bootstrap.get("n_resamples", 1000),
                    rng=bootstrap.get("rng", 2027),
                    confidence=bootstrap.get("confidence", 0.95),
                )
                note = f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"
        identifier = f"slice:{name}/{metric}"
        if verdict != "ok" and item.get("blocking"):
            blocked.append(identifier)
        label = "ok" if verdict == "ok" else ("MISSING" if verdict == "missing" else
                                               ("BLOCK" if item.get("blocking") else "warn"))
        lines.append(f"  {identifier:<32} {value!s:<8} {json.dumps(threshold):<40} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if not isinstance(pr.get("manifest"), dict) or not isinstance(base.get("manifest"), dict):
        return ["integrity"], ["  INTEGRITY missing report manifest"]
    if "eval_set_sha" not in pr["manifest"] or "eval_set_sha" not in base["manifest"]:
        return ["integrity"], ["  INTEGRITY missing eval_set_sha"]
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    ratchet_spec = base_spec or base.get("metric_spec")
    problems = integrity_check(pr, base, spec, ratchet_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
