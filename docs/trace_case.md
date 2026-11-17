# Trace case: ticket overrides the DB delay

Reproduce from `src/`:

```bash
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
```

| Field | Evidence |
|---|---|
| Trial | `seeded_regression C-002@11`; report run ID `E-seeded_regression-20261117-4982` |
| Symptom | The Lab 8 grader fails (`status resolved != denied`). The ledger contains 20,000 VND, while the independent label requires no refund. |
| First wrong step | Event 3, `model_override`: ticket delay 5 replaces the DB delay 2. |
| Why it is first | Events 1–2 retrieved the claim and structured order correctly. The quote at event 4 follows the corrupted delay and becomes 20,000 VND. |
| Failure mode | FM-03 `ticket_trust` |
| Fixed comparison | `fixed C-002@11` keeps the DB delay, quotes 0, and ends denied with ledger 0. |
| Regression test | `tests/test_lab9_trace_case.py::test_ticket_override_is_first_failure_and_fixed_shape_passes` verifies the override precedes the quote, the regression fails, and fixed passes. `DbFactKept` also flags the override. |
| Not proven | This one trace shows the first wrong recorded action for this seed; it does not estimate how often a real model would trust ticket text. |

The reply is fluent in the failing trace, but the ledger is the source of truth. This case is tagged
FM-03 in the v1 eval set; its expected label remains in the separate label file.
