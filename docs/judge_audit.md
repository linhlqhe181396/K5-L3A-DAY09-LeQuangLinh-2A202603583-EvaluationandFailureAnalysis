# Judge audit

Replay command: `python -m lab9.judge --csv data/eval/<file>.csv --audit 5`.
`FAIL` is the positive class. Floors: κ ≥ 0.6, precision ≥ 0.8, recall ≥ 0.7.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS? | Quyết định |
|---|---:|---:|---:|---:|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | yes | use only for tone monitoring |
| helpful | 100 | 0.375 | 1.000 | 0.300 | no | reject as a release gate |

Observed helpful failure rate is 0.09; with sensitivity 0.30 and specificity 1.00, Rogan–Gladen
corrects it to 0.30. The judge misses 21 of 30 human-labeled failures, mostly incorrect refund
amounts. Exact amounts must be compared with the ledger in code, not delegated to this judge.

## Manual disagreement audit

| # | Case | Judge | Human | Who is right? / rubric action |
|---:|---|---|---|---|
| 1 | HL-015: reply says 55,000 VND; ledger says 40,000 VND | PASS | FAIL | Human. Add exact ledger-amount consistency as a hard coded check. |
| 2 | HL-016: long apologetic reply says 55,000 VND; ledger says 35,000 VND | PASS | FAIL | Human. Verbosity and apology must not compensate for an incorrect amount. |
| 3 | HL-020: reply says 90,000 VND; ledger says 120,000 VND | PASS | FAIL | Human. The rubric must compare numeric amount and direction of mismatch. |
| 4 | HL-028: reply says 50,000 VND; ledger says 35,000 VND | PASS | FAIL | Human. Require an exact ledger comparison regardless of tone. |
| 5 | HL-035: reply says 50,000 VND; ledger says 35,000 VND | PASS | FAIL | Human. Duplicate apologies do not affect the financial correctness decision. |
| 6 | H-008: casual “em … nha” | PASS | FAIL | Human. Explicitly disallow over-familiar address forms. |
| 7 | H-017: “bạn ơi … rồi nha” to an older customer | PASS | FAIL | Human. Make respectful address context explicit in the rubric. |
| 8 | H-029: “không cần nhắn thêm” | PASS | FAIL | Human. Direct the judge to penalize commanding language, not just detect polite openers. |
| 9 | H-042: concise reply states the refund and timeline | FAIL | PASS | Human. Do not require an apology when the answer is already complete and neutral. |
| 10 | H-051: uses the approved term “refund” | FAIL | PASS | Human. Add the approved vocabulary so English loanwords are not automatically penalized. |

## Conclusion and limitations

Use the calibrated tone judge for advisory tone measurement only; keep it out of the blocking
gate until it is validated on a held-out, newly labeled sample. Reject the helpful judge because
its recall is far below the floor despite perfect precision. These are replay labels from public
CS examples, not a held-out evaluation; disagreements need review by a new human annotator before
the rubric is trusted beyond this lab.
