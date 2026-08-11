# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: «điền tên nhóm»
- Repository URL: https://github.com/BinhAnndapoet/Day13-K3-Observability
- Commit SHA cuối: «điền SHA sau khi push»
- Thành viên và vai trò:
  - **Thành viên A** — Tech Lead / Backend Engineer: CP1 (middleware, correlation ID, enrichment log, PII scrubbing).
  - **Thành viên B** — SRE & Alerts Engineer: CP2 (cấu hình Langfuse, SLO, alert rules, alert runbook).
  - **Thành viên C** — QA & Chief Investigator: dashboard spec + trình dựng dashboard, load test, challenge/incident (CP3), rà soát chất lượng toàn repo, tổng hợp báo cáo.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** (`submission/evidence/validate_logs_baseline.txt`) — 0 PII leak, 0 record thiếu required field, 0 record thiếu enrichment.
- Kết quả `validate_dashboard.py`: **HỢP LỆ: 6/6 panel** (`submission/evidence/validate_dashboard.txt`).
- Public tests: **40 passed** (`python -m pytest -q`).
- Số PII leak còn lại: **0**.
- Tổng số traces trên Langfuse: **0 — chưa có key Langfuse**, xem mục 4.
- Dashboard: `submission/evidence/dashboard_baseline.png` (dựng bằng `scripts/build_dashboard.py` từ `data/logs.jsonl`).

Số liệu ba cửa sổ đo (chi tiết ở `submission/evidence/README.md`):

| Cửa sổ | Request | P95 `latency_ms` (đo trong agent) | P95 `duration_ms` (người dùng thấy) | Error rate | Cost | Quality |
|---|---|---|---|---|---|---|
| Baseline | 50 | 151 ms | — (chưa có log này) | 0.00% | $0.1022 | 0.88 |
| Challenge `rag_slow` | 15 | 2,651 ms | **13,297 ms** | 0.00% | $0.0303 | 0.86 |
| Sau fix (`rag_slow` vẫn bật) | 15 | 2,657 ms | **2,706 ms** | 0.00% | $0.0292 | 0.86 |

## 3. Logging và tracing

- **Evidence correlation ID**: `submission/evidence/log_correlation_and_pii.txt` mục 1 — hai dòng `request_received` và `response_sent` của cùng một request đều mang `correlation_id: req-2d3641cf`, kèm `user_id_hash`, `session_id`, `feature`, `model`, `env`. ID được sinh ở `app/middleware.py` và bind vào `structlog.contextvars`, nên mọi dòng log sau đó tự động có.
- Correlation ID nhận từ header `x-request-id` **chỉ khi đúng format** `req-<8 hex>`; giá trị lạ do client gửi lên bị bỏ và sinh mới (`app/middleware.py`).
- **Evidence PII redaction**: `log_correlation_and_pii.txt` mục 2 — ba query mẫu trong `data/sample_queries.jsonl` (dòng `s01` chứa email, `s05` chứa số điện thoại, `s09` chứa số thẻ) xuất hiện trong log dưới dạng `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]`. Giá trị gốc không được chép lại vào báo cáo này.
- Thứ tự processor trong `app/logging_config.py` đặt `scrub_event` **sau** `format_exc_info`, nên PII nằm trong traceback cũng bị che (regression test `tests/test_logging_scrub.py`).
- **Evidence trace waterfall**: chưa có — phụ thuộc CP2, xem mục 4.
- **Giải thích một span đáng chú ý**: span `retrieve()` trong `LabAgent.run` chiếm gần như toàn bộ latency khi incident `rag_slow` bật (2.5s trên tổng 2.65s). Phân tích đầy đủ ở mục 6.

## 4. Prompt versioning

**Trạng thái: chưa hoàn thành.** `/health` trả `tracing_enabled: false` vì `.env` chưa có `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`, nên trace metadata hiện ghi `prompt_source=local`, `prompt_version=local-v1`.

- Prompt name: `day13-chat` (theo `LANGFUSE_PROMPT_NAME`)
- Version/label baseline: chưa tạo
- Version/label candidate: chưa tạo
- Trace ID của mỗi version: chưa có
- Bằng chứng đổi label hoặc rollback: chưa có

Phần code phía app đã sẵn sàng và có test: `app/prompt_management.py` fetch prompt theo name+label, `app/agent.py` gắn `prompt_name` / `prompt_label` / `prompt_version` / `prompt_source` vào cả trace lẫn generation, và `tests/test_agent_prompt_trace.py` chứng minh liên kết đó. Chỉ còn thiếu key Langfuse + thao tác tạo v1/v2, đổi label và rollback theo `docs/PROMPT_VERSIONING.md`.

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: **HỢP LỆ: 6/6 panel** — `submission/evidence/validate_dashboard.txt`
- Evidence dashboard: `submission/evidence/dashboard_baseline.png`, `dashboard_challenge.png`, `dashboard_afterfix.png` (kèm file `.html` tương ứng để mở lại)
- Thiết kế dashboard: [`docs/dashboard-spec.md`](../docs/dashboard-spec.md) — dashboard được **sinh từ contract**: `scripts/build_dashboard.py` đọc ngưỡng/đơn vị/event từ `config/dashboard.yaml` và số liệu từ `data/logs.jsonl`, nên không thể lệch contract.
- SLO đã chọn và lý do ([`config/slo.yaml`](../config/slo.yaml)):
  - `latency_p95_ms`: Objective ≤ 3000ms (Target 99.5%) — đảm bảo trải nghiệm phản hồi nhanh.
  - `error_rate_pct`: Objective ≤ 2% (Target 99.0%) — giữ tỉ lệ request thất bại ở mức tối thiểu.
  - `daily_cost_usd`: Objective ≤ $2.5/ngày (Target 100%) — tránh vượt ngân sách API LLM.
  - `quality_score_avg`: Objective ≥ 0.75 (Target 95%) — đảm bảo chất lượng câu trả lời.
- Alert rules: [`config/alert_rules.yaml`](../config/alert_rules.yaml) — `high_latency_p95`, `high_error_rate`, `cost_spike`, đều symptom-based và tham chiếu đúng tên metric có thật trong `/metrics`.
- Alert runbook: [`docs/alerts.md`](../docs/alerts.md) — mỗi alert có 3 bước Metrics → Traces → Logs và mitigation tạm thời.

### Hai điểm yếu của bộ SLO/alert mà challenge đã phơi ra

1. **Ngưỡng 3000ms không bắt được sự cố này.** Trong challenge, P95 `latency_ms` = 2,651ms — *dưới* ngưỡng, dashboard vẫn báo "Đạt ngưỡng", trong khi người dùng thật chờ 13.3s. Alert `high_latency_p95` sẽ **không** kêu.
2. **Alert đặt đúng bằng objective SLO nên không còn error budget.** Khi alert kêu thì SLO đã vỡ chứ không phải sắp vỡ.

Đề xuất: thêm alert trên `duration_ms` (wall-clock, xem mục 6) với ngưỡng cảnh báo sớm ~2000ms — trùng `latency_threshold_ms` mà chính challenge dùng.

## 6. Điều tra challenge

- **Challenge ID**: `day13-k3-observability-v1` (cohort K3, `incident: rag_slow`, `affected_feature: refund`, `latency_threshold_ms: 2000`, seed 1303)
- **Lệnh đã chạy**: `python scripts/inject_incident.py` rồi `python scripts/load_test.py --challenge --concurrency 5` (3 đợt cách nhau ~50s).

### Bước 1 — Triệu chứng từ metrics

`submission/evidence/metrics_challenge.json` so với `metrics_baseline.json`:

| Chỉ số | Baseline | Challenge | Thay đổi |
|---|---|---|---|
| `latency_p50` | 150 ms | 2,651 ms | ×17.7 |
| `latency_p95` | 151 ms | 2,651 ms | ×17.6 |
| `error_rate_pct` | 0.00% | 0.00% | không đổi |
| `quality_avg` | 0.88 | 0.86 | gần như không đổi |
| token/request | ~130 | ~130 | không đổi |

Đọc được ngay: latency tăng vọt nhưng **error rate, cost/request và token đều không đổi** → không phải lỗi, không phải cost spike, mà là một bước xử lý bị chậm. Panel Latency trong `dashboard_challenge.png` cho thấy P50/P95/P99 đều dồn về 2,651ms — phân phối rất "phẳng", dấu hiệu của độ trễ **cố định** cộng thêm chứ không phải tail latency ngẫu nhiên.

### Bước 2 — Khoanh vùng span

Langfuse chưa có trace (mục 4), nên phần khoanh vùng span được làm bằng dữ liệu tương đương trong log và code:

- `latency_ms` được đo trong `LabAgent.run` (`app/agent.py`), bao trọn `retrieve()` + `llm.generate()`.
- Baseline: `latency_ms` ≈ 150ms, trong đó `FakeLLM.generate` cố định `time.sleep(0.15)` → LLM chiếm ~150ms, retrieval ~0ms.
- Challenge: `latency_ms` ≈ 2,651ms; phần LLM vẫn 150ms (token và cost không đổi) → **toàn bộ 2.5s tăng thêm nằm ở span retrieval**.

Đúng bằng `time.sleep(2.5)` trong `app/mock_rag.py`, nhánh chỉ chạy khi `STATE["rag_slow"]` bật.

### Bước 3 — Chứng minh bằng log

Client lại thấy 13.3s chứ không phải 2.65s (`load_test_challenge.txt`). Chênh lệch được chứng minh bằng log, đối chiếu theo `correlation_id`:

| correlation_id | `latency_ms` (trong agent) | `duration_ms` (wall-clock) | Thời gian chờ hàng đợi |
|---|---|---|---|
| `req-03e599b1` | 2,651 | 13,297 | 10,646 |
| `req-fa712e1f` | 2,651 | 13,296 | 10,645 |
| `req-f6963d6e` | 2,651 | 13,295 | 10,644 |
| `req-743fd907` | 2,651 | 13,293 | 10,642 |
| `req-e4247e8d` | 2,651 | 13,290 | 10,639 |

Với concurrency = 5, request cuối chờ đúng 4 × 2.66s ≈ 10.6s. Đây là dấu hiệu kinh điển của **serialization**: 5 request lẽ ra chạy song song lại xếp hàng nối đuôi.

### Root cause

Hai tầng:

1. **Nguyên nhân trực tiếp**: incident `rag_slow` bật nhánh `time.sleep(2.5)` trong `app/mock_rag.py` (mô phỏng vector store chậm), cộng thẳng 2.5s vào mỗi request.
2. **Nguyên nhân khuếch đại (lỗi thật của app)**: `agent.run()` là hàm **đồng bộ** dùng `time.sleep`, nhưng được gọi trực tiếp trong route `async def chat`. Nó **chặn event loop**, nên trong lúc một request ngủ 2.5s thì mọi request khác không được xử lý. Độ trễ nhân lên theo số request đồng thời: 2.65s → 13.3s ở concurrency 5, và tệ hơn nữa khi tải cao hơn.

Chính lỗi thứ hai làm sự cố **vô hình với dashboard**: `latency_ms` chỉ đếm thời gian bên trong `agent.run`, không tính thời gian nằm chờ, nên P95 hiển thị 2,651ms < SLO 3000ms trong khi người dùng chịu 13.3s.

### Fix action

Đưa lời gọi blocking sang threadpool để nó không chặn event loop (`app/main.py`):

```python
result = await run_in_threadpool(agent.run, user_id=..., feature=..., session_id=..., message=...)
```

Đo lại với **`rag_slow` vẫn bật** (`load_test_afterfix.txt`; `afterfix_incident_state.txt` xác nhận incident chưa tắt):

| | P95 `latency_ms` | P95 `duration_ms` |
|---|---|---|
| Trước fix | 2,651 ms | 13,297 ms |
| Sau fix | 2,657 ms | **2,706 ms** |

Độ trễ người dùng giảm **4.9 lần**, phần chờ hàng đợi gần như biến mất (13,297 → 2,706, chỉ còn ~50ms overhead). Phần 2.5s còn lại đúng bằng độ chậm do incident tạo ra — muốn hết thì phải tắt incident (`python scripts/inject_incident.py --disable`) hoặc sửa vector store.

### Preventive measure

1. **Log wall-clock thật cho mọi request** (đã triển khai, `app/middleware.py`): thêm event `request_completed` với `duration_ms`, `status_code`, `path`, `service="http"`. Đây là con số phản ánh trải nghiệm người dùng; nếu chỉ có `latency_ms` thì sự cố này không bao giờ hiện lên dashboard. Regression test: `tests/test_middleware_correlation_id.py::test_wall_clock_duration_is_logged_and_covers_agent_latency`.
2. **Alert trên `duration_ms`, không chỉ trên `latency_ms`**, với ngưỡng cảnh báo sớm 2000ms (đúng `latency_threshold_ms` của challenge) trước khi chạm SLO 3000ms.
3. **Chặn blocking I/O trong route async** ở khâu review: hàm đồng bộ có I/O phải đi qua `run_in_threadpool` hoặc được viết lại thành `async`.
4. **Load test có concurrency trong quy trình kiểm thử**: sự cố này chỉ lộ ra khi chạy `--concurrency 5`; chạy tuần tự thì cả hai số đều là 2.65s và không ai thấy vấn đề.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Thành viên A (Tech Lead/Backend) | CP1: `CorrelationIdMiddleware`, bind context enrichment trong `/chat`, bật `scrub_event`, thêm `error_rate_pct` vào `/metrics`, exception handler trả 500 kèm correlation ID | `9215be8` | Correlation ID phải được bind vào context **trước** dòng log đầu tiên thì mọi log sau mới kế thừa được |
| Thành viên B (SRE & Alerts) | CP2: `config/slo.yaml`, `config/alert_rules.yaml`, runbook `docs/alerts.md`, đưa `correlation_id` vào trace metadata; sửa lỗi định nghĩa trùng `configure_logging` của CP1 (bản trùng làm PII scrubbing bị vô hiệu) | `043616f` | Luồng Metrics → Traces → Logs; cách đặt ngưỡng SLO theo UX và chi phí; alert phải symptom-based |
| Thành viên C (QA & Chief Investigator) | Dashboard spec + `scripts/build_dashboard.py` (6 panel sinh từ contract); load test baseline/challenge; điều tra CP3, fix threadpool và biện pháp phòng ngừa `duration_ms`; rà soát và sửa 6 lỗi của CP1/CP2; +18 test | «điền SHA» | `latency_ms` đo trong ứng dụng có thể *hoàn toàn* che giấu độ trễ người dùng thật; percentile phải dùng nearest-rank; PII phải được scrub sau khi traceback đã render thành chuỗi |

### Chi tiết phần rà soát chất lượng (thành viên C)

Sáu lỗi được phát hiện và sửa, mỗi lỗi kèm regression test:

| # | File | Lỗi | Hệ quả nếu không sửa |
|---|---|---|---|
| 1 | `app/logging_config.py` | `scrub_event` chạy trước `format_exc_info` | PII trong traceback lọt xuống log; `validate_logs.py` mất 30 điểm ngay khi có một `log.exception` |
| 2 | `app/pii.py` | pattern địa chỉ không có `IGNORECASE` và chỉ che từ khóa | "Đường Láng" không bị che; "đường Láng" chỉ mất chữ "đường", tên đường vẫn còn |
| 3 | `app/middleware.py` | nhận `x-request-id` từ client không kiểm tra format | client gửi `x-request-id: MISSING` làm hỏng truy vết và bị validator đếm là thiếu field |
| 4 | `app/metrics.py` | `percentile` lệch 1 bậc với p50 khi `n*p/100` là số nguyên | P50 báo cao hơn thực tế (n=10 trả 60 thay vì 50) |
| 5 | `app/main.py` | handler 500 tổng quát không log, không `record_error` | lỗi ngoài route trả 500 "câm", không hiện trên panel Errors |
| 6 | `app/main.py` | import `JSONResponse` trùng, TODO thừa | rác trong diff |

Ngoài ra thêm `tests/conftest.py` để test không ghi vào `data/logs.jsonl` thật — trước đó mỗi lần chạy `pytest` là evidence dashboard bị lẫn traffic không có thật.

## 8. Việc còn lại trước khi nộp

- [ ] **Cấu hình Langfuse** (thành viên B): điền key vào `.env`, tạo ≥10 traces, tạo prompt `day13-chat` v1/v2, gắn label, thực hiện rollback, chụp evidence → điền mục 4 và cập nhật `submission/evidence/README.md`.
- [ ] Điền tên nhóm và commit SHA cuối vào mục 1.
- [ ] Chạy lại `python -m pytest -q`, `python scripts/validate_logs.py`, `git status --short` trước khi push.
