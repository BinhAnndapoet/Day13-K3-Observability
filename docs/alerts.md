# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: high_latency_p95
- Severity: Critical
- SLI/SLO liên quan: Latency P95 (SLO: latency_p95 ≤ 3000ms, Target: 99.5%)
- Điều kiện và thời gian duy trì: `latency_p95 > 3000ms` duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng bị phản hồi chậm, tăng khả năng timeout request trên client.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở Panel 1 (Latency percentiles) trên Dashboard, kiểm tra xu hướng P50, P95, P99 và thời điểm spike.
  2. **Traces**: Mở Langfuse UI, lọc các trace có `latency > 3000ms` trong khung thời gian bị ảnh hưởng. Xác định span chiếm phần lớn latency (ví dụ: RAG retrieval span vs LLM generation span).
  3. **Logs**: Tra cứu log bằng `correlation_id` của trace bị chậm trong `data/logs.jsonl`. Đọc log event `request_received` và `response_sent` để tìm tham số request hoặc lỗi nội bộ.
- Mitigation tạm thời: Nếu phát hiện incident `rag_slow` đang bật hoặc VectorDB bị nghẽn, gọi API `/incidents/rag_slow/disable` hoặc chuyển hướng sang fallback retrieval nhẹ hơn.
- Owner: sre-team

## Alert 2

- Tên: high_error_rate
- Severity: Critical
- SLI/SLO liên quan: Error Rate Percentage (SLO: error_rate_pct ≤ 2%, Target: 99.0%)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` duy trì trong 3 phút
- Ảnh hưởng tới người dùng: Khách hàng nhận lỗi HTTP 500 (`request_failed`), ứng dụng gián đoạn tính năng QA/Summary.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở Panel 3 (Error rate and breakdown) trên Dashboard, kiểm tra tỉ lệ lỗi tổng và phân rã theo `error_type` (e.g., RuntimeError, TimeoutError).
  2. **Traces**: Trên Langfuse UI, tìm các trace chứa status `ERROR` hoặc có exception thrown để xem span cụ thể bị lỗi (như tool call hoặc LLM call).
  3. **Logs**: Tìm các dòng log event `request_failed` trong `data/logs.jsonl`, kiểm tra trường `error_type` và `payload.detail` với `correlation_id` tương ứng để thấy chi tiết exception.
- Mitigation tạm thời: Nếu lỗi do tool hoặc dependency bên ngoài (ví dụ: `tool_fail`), tắt incident bằng POST `/incidents/tool_fail/disable` hoặc bật fallback response cho agent.
- Owner: sre-team

## Alert 3

- Tên: cost_spike
- Severity: Warning
- SLI/SLO liên quan: Daily Cost USD (SLO: daily_cost_usd ≤ 2.5 USD/ngày, Target: 100.0%)
- Điều kiện và thời gian duy trì: `total_cost_usd > 2.5` trong cửa sổ 24 giờ (hoặc tốc độ tăng cost theo phút vượt bất thường)
- Ảnh hưởng tới người dùng: Không ảnh hưởng trực tiếp tới UX nhưng vượt ngân sách vận hành của hệ thống AI.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở Panel 4 (Cost over time) và Panel 5 (Input and output tokens) trên Dashboard để xác định nguồn gốc gia tăng cost (do số lượng request tăng hay do output token spike).
  2. **Traces**: Tìm trên Langfuse các trace có `cost_details.total` hoặc `completion_tokens` cao bất thường để xem generation prompt và response.
  3. **Logs**: Lọc log event `response_sent` có `tokens_out` lớn hoặc `cost_usd` cao, dùng `correlation_id` đối chiếu prompt version/model đang sử dụng (`prompt_version`, `model`).
- Mitigation tạm thời: Tắt incident `cost_spike` nếu đang bật (`/incidents/cost_spike/disable`), hoặc kiểm tra và rollback prompt về version ngắn gọn hơn (`baseline`).
- Owner: sre-team
