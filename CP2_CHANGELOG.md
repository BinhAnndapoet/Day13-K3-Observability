# Changelog & Báo cáo công việc - Checkpoint 2 (CP2)

File này tóm tắt toàn bộ các thay đổi tôi đã thực hiện trên codebase để giúp Thành viên B (SRE & Alerts Engineer) hoàn thành nhiệm vụ CP2.

## 1. Cấu hình Alert Rules (`config/alert_rules.yaml`)
Đã thay thế các `TODO` bằng 3 rule cảnh báo thực tế dựa trên triệu chứng (symptom-based):
- **high_latency_p95**: Báo động mức `critical` khi P95 Latency > 3000ms kéo dài trong 5 phút.
- **high_error_rate**: Báo động mức `critical` khi tỉ lệ lỗi vượt 2% kéo dài trong 3 phút.
- **cost_spike**: Báo động mức `warning` khi tổng chi phí API LLM vượt $2.5 trong khoảng thời gian 24 giờ.
Tất cả đều được gán cho owner là `sre-team` và dẫn link đến file runbook tương ứng.

## 2. Viết Alert Runbook (`docs/alerts.md`)
Đã điền đầy đủ nội dung vào template trống. Với mỗi alert (Latency, Error Rate, Cost), runbook cung cấp:
- Mức độ nghiêm trọng (Severity) và mục tiêu SLI/SLO liên kết.
- Tác động trực tiếp đến trải nghiệm người dùng (UX).
- **3 bước kiểm tra (Triage steps)** đi đúng theo luồng chuẩn của lab:
  1. **Metrics**: Nhìn Dashboard panel nào.
  2. **Traces**: Lọc trace trên Langfuse UI ra sao.
  3. **Logs**: Dùng `correlation_id` tra log trong `data/logs.jsonl` như thế nào.
- Các hành động khắc phục tạm thời (Mitigation) như gọi API disable incident hoặc rollback prompt.

## 3. Bổ sung thông tin SLO (`config/slo.yaml`)
- Thêm các trường `note` giải thích rõ ý nghĩa kinh doanh và mục tiêu của 4 SLI (`latency_p95_ms`, `error_rate_pct`, `daily_cost_usd`, `quality_score_avg`).

## 4. Dọn dẹp & Vá lỗi Code
- **`app/logging_config.py`**: Xóa bỏ khai báo hàm `configure_logging()` bị lặp lại, giữ lại phiên bản chuẩn và đảm bảo `scrub_event` (bộ lọc PII) hoạt động bình thường, không bị ghi đè.
- **`app/agent.py`**: Fix lỗi logic khi ghi `correlation_id` vào trace metadata. Thay đổi này giúp vượt qua 100% test case (đặc biệt là test `test_agent_prompt_trace.py` vốn bị lỗi do metadata dictionary mismatch).

## 5. Cập nhật Báo cáo (`submission/REPORT.md`)
- Điền đầy đủ thông tin vào **Section 5** (Dashboard, SLO và alerts), map đúng 6 panel và 4 SLO.
- Điền **Section 7** (Đóng góp cá nhân) cho Thành viên B, liệt kê rõ các file đã thay đổi và kỹ năng học được.

---
**Kết quả Validate:**
- `python scripts/validate_dashboard.py` ➡️ `HỢP LỆ: 6/6 panel`
- `python -m pytest -q` ➡️ `22 passed in 1.54s` (Pass 100%)
