# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`:
- Tổng số traces:
- Số PII leak còn lại:
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: HỢP LỆ: 6/6 panel
- Evidence dashboard: `submission/evidence/dashboard_6panels.png`
- SLO đã chọn và lý do:
  - `latency_p95_ms`: Objective ≤ 3000ms (Target: 99.5%) - Đảm bảo trải nghiệm phản hồi nhanh của người dùng.
  - `error_rate_pct`: Objective ≤ 2% (Target: 99.0%) - Giữ tỉ lệ request thất bại ở mức tối thiểu.
  - `daily_cost_usd`: Objective ≤ $2.5/ngày (Target: 100.0%) - Tránh vượt ngân sách API LLM.
  - `quality_score_avg`: Objective ≥ 0.75 (Target: 95.0%) - Đảm bảo chất lượng câu trả lời từ RAG & LLM.
- Alert rules và runbook:
  - Alert rules: [config/alert_rules.yaml](file:///c:/Users/Tunnne/Downloads/code/Day13-K3-Observability/config/alert_rules.yaml) (Bao gồm `high_latency_p95`, `high_error_rate`, `cost_spike`)
  - Alert runbook: [docs/alerts.md](file:///c:/Users/Tunnne/Downloads/code/Day13-K3-Observability/docs/alerts.md) (Quy trình 3 bước Metrics → Traces → Logs cho từng alert)

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Thành viên B (SRE & Alerts Engineer) | Cấu hình Langfuse, thiết lập SLO (config/slo.yaml), Alert Rules (config/alert_rules.yaml), viết Runbook (docs/alerts.md) và validate Dashboard contract | Commit | Hiểu luồng khắc phục sự cố Metrics → Traces → Logs, cách đặt ngưỡng SLO dựa trên UX và chi phí, và thiết kế symptom-based alerts. |
| | | | |

