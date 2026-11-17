# src/reports/

Mọi lệnh dưới đây chạy trong thư mục `src/`, nên file JSON được ghi vào `src/reports/`.

Nhóm **commit** các file do công cụ của lab sinh ra. Đây là bằng chứng nộp bài:
Thư mục `src/reports/` bị `.gitignore` bỏ qua; dùng `git add -f <đường-dẫn-báo-cáo>` cho các file
cần nộp, không dùng `git add -A` để chờ chúng tự được thêm.

| File | Lệnh tạo | Bắt buộc |
| --- | --- | --- |
| `benchmark.json` | `python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json` | Có |
| `crash.json` | `python -m lab8.crash_test --count 20 --out reports/crash.json` | Có |
| `baseline_v1.json` | `python -m lab9.eval --shape swarm --spec config/metric_spec.yaml --out reports/baseline_v1.json` | Có |
| `eval_fixed.json`, `eval_seeded_regression.json` | `python -m lab9.eval --shape fixed` / `seeded_regression` | Có |
| `baseline_v2.json` | `python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/baseline_v2.json` | Advanced |
| `eval_fixed_v2.json` | `python -m lab9.eval --shape fixed --spec config/metric_spec_v2.yaml --out reports/eval_fixed_v2.json` | Advanced |
| `eval_slice_regression.json`, `eval_flaky_regression.json` | `python -m lab9.eval --shape slice_regression` / `flaky_regression` with the v2 spec | Advanced |
| `traps/*.json` | `python -m lab9.traps --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml` | Expert |
| `hidden_selfcheck.json` | benchmark trên `student_drop/` (xem `src/README.md`, mục Tự kiểm trên bộ hidden) | Không |
| `bonus_*.json` | script bonus của nhóm | Chỉ khi làm bonus |

Không sửa tay file JSON. Giảng viên chạy lại đúng các lệnh trên trên máy chấm. Số không khớp thì mục Reproducibility mất điểm. `hidden_grade.json` chỉ giảng viên tạo và bị gitignore.
