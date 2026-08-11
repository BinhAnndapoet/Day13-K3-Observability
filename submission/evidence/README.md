# Chỉ mục evidence

Đối chiếu với danh sách bắt buộc trong [SUBMISSION.md](../../SUBMISSION.md) và [docs/grading-evidence.md](../../docs/grading-evidence.md).

## Thứ tự thời gian của ba lần đo

| # | Cửa sổ (UTC) | Trạng thái hệ thống | File |
|---|---|---|---|
| 1 | 04:09:16 → 04:13:51 | baseline, không incident | `*_baseline.*` |
| 2 | 04:24:10 → 04:30:09 | challenge `rag_slow` **bật**, code chưa fix | `*_challenge.*` |
| 3 | 04:32:25 → 04:35:47 | challenge `rag_slow` **vẫn bật**, đã fix threadpool | `*_afterfix.*` |

Lần đo 1 chạy trước khi thêm log `request_completed` (biện pháp phòng ngừa được thêm ngay trong lúc điều tra), nên `logs_baseline.jsonl` chưa có event này. Lần 2 và 3 đều có.

## Bản đồ evidence → yêu cầu

| Yêu cầu | File |
|---|---|
| Kết quả `validate_logs.py` | `validate_logs_baseline.txt` (100/100), `validate_logs_challenge.txt` |
| Kết quả `validate_dashboard.py` | `validate_dashboard.txt` (`HỢP LỆ: 6/6 panel`) |
| Dashboard đủ 6 nhóm chỉ số | `dashboard_baseline.png` / `.html`, `dashboard_challenge.png`, `dashboard_afterfix.png` |
| Log có correlation ID và metadata | `log_correlation_and_pii.txt` mục 1 |
| Bằng chứng PII đã redact | `log_correlation_and_pii.txt` mục 2 |
| Bằng chứng điều tra challenge | `challenge_incident_enable.txt`, `load_test_challenge.txt`, `metrics_challenge.json`, `logs_challenge.jsonl` |
| Bằng chứng fix có hiệu lực | `load_test_afterfix.txt`, `metrics_afterfix.json`, `dashboard_afterfix.png` |
| Danh sách ≥ 10 traces | **CHƯA CÓ** — cần key Langfuse (CP2) |
| Trace waterfall | **CHƯA CÓ** — cần key Langfuse (CP2) |
| Hai prompt version + trace gắn đúng version/label | **CHƯA CÓ** — cần key Langfuse (CP2) |
| Bằng chứng đổi label / rollback prompt | **CHƯA CÓ** — cần key Langfuse (CP2) |

## Cách tái lập

```bash
uvicorn app.main:app --port 8000            # terminal 1
python scripts/load_test.py --concurrency 5 # terminal 2, lặp vài lần cách nhau ~50s
python scripts/validate_logs.py
python scripts/validate_dashboard.py
python scripts/build_dashboard.py --label "Baseline" --out submission/evidence/dashboard_baseline.html
```

Ảnh PNG được render từ file HTML tương ứng bằng Chrome headless:

```bash
chrome --headless=new --window-size=1500,1000 --screenshot=dashboard_baseline.png dashboard_baseline.html
```

## Lưu ý về dữ liệu

Các file `logs_*.jsonl` là log **đã qua PII scrubbing** của app (email/điện thoại/thẻ đã thành `[REDACTED_*]`), `user_id` đã được hash. Không có secret hay `.env` trong thư mục này.
