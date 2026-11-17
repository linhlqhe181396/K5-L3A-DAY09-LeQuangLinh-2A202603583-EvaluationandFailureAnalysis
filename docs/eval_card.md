# Eval card — LogiX-VN refund agent

## v1

- **Run / eval-set SHA:** `E-swarm-20261117-4982` / `4982798330f9`
- **Runtime:** Python 3.11.9 · implementation in this worktree · eval set v1 ·
  metric spec 1.0 · seeds 11/22/33/44/55
- **Eval set:** 14 public items × 5 seeds; labels in `data/eval/labels_v1.json`.
- **Metrics and thresholds:** see `config/metric_spec.yaml`; safety caps are zero, outcome floors
  are 0.85–0.95 depending on metric.
- **Integrity:** the report embeds the evaluated metric spec; gate checks report/spec agreement and
  ratchets against the baseline's embedded spec.
- **Baseline:** pass rate 0.9857; refund amount 0.9857; proposal amount 0.9857; reply/ledger
  consistency 1.0000; pass_5 0.9286; approval bypass 0; secret leaks 0.
- **Fixed comparison:** `E-fixed-20261117-4982` passes. Δ pass rate +0.014; paired 95% CI
  [+0.000, +0.043].
- **Regression comparison:** `E-seeded_regression-20261117-4982` is blocked. Δ pass rate −0.271;
  paired 95% CI [−0.500, −0.057].
- **Judge:** tone κ=0.757, P=0.857, R=0.800 (monitoring only); helpful κ=0.375, P=1.000,
  R=0.300 (rejected because of low recall).
- **Trace case:** `docs/trace_case.md`, C-002@11; first wrong event is the ticket-driven
  `model_override`. The regression test is
  `tests/test_lab9_trace_case.py::test_ticket_override_is_first_failure_and_fixed_shape_passes`.
- **Gate owner:** team evaluation owner; gate exit 1 blocks merge until reviewed.
- **Pilot:** public, single-claim refunds and denials only; no production users or real payments.
- **Limits:** MockLLM, 14 items, five seeds, and public judge replay. A bug occurring on 1/3 seeds
  cannot be reliably detected from five repetitions. The swarm reference omits reply events, so
  reply/ledger consistency is not assessable for those rows.
- **Eval-set versioning:** add cases or change labels only with a new eval-set version and a new
  generated baseline. Keep the metric-spec ratchet strict for an unchanged set.

## v2 (Advanced / Expert)

- **Eval set:** 28 items (14 public + 14 adversarial) × 5 seeds; SHA `611dcd4bb409`.
- **Baseline:** `E-swarm-20261117-611d`; pass rate 0.9786, pass_hat_5 0.8929.
- **Noise rule:** A/A seeds 66/77/88/99/110 produced Δ=0.0000 for every metric under deterministic
  MockLLM. Therefore the pass_hat_5 floor is 0.80, below the 0.8929 baseline and outside the
  observed zero-noise boundary; this is not evidence that a real LLM has zero noise.
- **Slices:** `money_movement` catches `slice_regression` (slice pass rate 0.85, CI Δ
  [−0.300, +0.000]); `adversarial` and `denial` are also blocking. `pass_hat_5` catches
  `flaky_regression` (0.5714) despite its pass rate remaining 0.9143.
- **Mutation:** public scorecard 3/3 regressions blocked, zero false alarms (`fixed` and
  `honest_refactor` merge).
- **Fixed v2 comparison:** `E-fixed-20261117-611d` passes with pass rate and pass_hat_5 both 1.0.
- **Integrity:** all four public traps are blocked: evaluator errors as NaN, dropped failing rows,
  cherry-picked seeds, and loosened spec.
- **Limits:** five seeds cannot reliably detect a bug affecting only one of three repetitions.
  Add targeted repetitions or a dedicated regression test; do not lower the gate until it passes.
