# Yêu cầu dashboard

Contract có thể kiểm tra bằng máy nằm tại `config/dashboard.yaml`. Hướng dẫn dựng và kiểm tra runtime nằm tại [DASHBOARD_SETUP.md](DASHBOARD_SETUP.md).

Dashboard chính cần đủ 6 nhóm thông tin:

1. Latency P50/P95/P99.
2. Traffic: request count hoặc QPS.
3. Error rate và breakdown theo loại lỗi.
4. Cost theo thời gian.
5. Tổng token input/output.
6. Quality proxy.

Tiêu chuẩn trình bày:

- Khoảng thời gian mặc định: 1 giờ.
- Tự refresh mỗi 15–30 giây nếu công cụ hỗ trợ.
- Có threshold hoặc SLO line.
- Ghi rõ đơn vị.
- Chỉ giữ 6–8 panel quan trọng ở lớp chính.
- Screenshot phải nhìn được tên panel và khoảng thời gian.

Kiểm tra contract trước khi chụp evidence:

```bash
python scripts/validate_dashboard.py
```

---

## Thiết kế cụ thể của nhóm (thành viên C)

Dashboard được sinh bằng `scripts/build_dashboard.py`, đọc **cùng lúc** hai file để không bao giờ lệch contract:

- ngưỡng, đơn vị, event và field: `config/dashboard.yaml`;
- số liệu: `data/logs.jsonl` (đúng nguồn chuẩn mà `DASHBOARD_SETUP.md` quy định).

```bash
python scripts/build_dashboard.py --label "Baseline" --out submission/evidence/dashboard_baseline.html
```

Output là một file HTML standalone (không cần server, không cần dependency ngoài `PyYAML`), mở bằng trình duyệt để chụp evidence.

### Chọn dạng biểu đồ theo việc mà người đọc phải làm

| Panel | Dạng | Vì sao |
|---|---|---|
| Latency | 3 cột P50/P95/P99 + đường SLO 3000ms | ba giá trị **có thứ tự** → ordinal ramp một tông xanh, đậm dần; đường threshold cho biết vượt hay chưa ngay lập tức |
| Traffic | cột theo phút | chuỗi thời gian, một series duy nhất → một màu |
| Errors | meter tỉ lệ lỗi so với giới hạn 2% + cột breakdown theo `error_type` | một tỉ lệ so với một ngưỡng là meter, không phải pie 2 lát; breakdown là series riêng |
| Cost | cột USD theo phút + tổng cửa sổ | thấy được cost tăng do traffic hay do token |
| Tokens | 2 cột `tokens_in` / `tokens_out` | hai series khác nhau → 2 màu categorical + legend + direct label |
| Quality | meter điểm trung bình với mốc 0.75 | một số duy nhất → meter/stat, không vẽ line 1 điểm |

### Quy tắc màu và trình bày

- Một trục duy nhất cho mọi panel; **không** dùng dual-axis.
- Categorical dùng đúng 2 slot (`#2a78d6` xanh, `#eb6834` cam) cho panel Tokens; ordinal ramp một tông (`#86b6ef → #2a78d6 → #104281`) cho Latency. Cả hai bộ đã chạy qua validator colorblind-safe ở cả light và dark mode.
- Màu trạng thái (`#0ca30c` đạt / `#d03b3b` vượt) **chỉ** dùng cho chip trạng thái và meter, không bao giờ dùng làm màu series, và luôn đi kèm icon + chữ nên không phụ thuộc màu.
- Threshold luôn là đường liền nét màu critical, có nhãn ghi rõ giá trị; gridline là hairline mảnh hơn.
- Mỗi panel có **table view** (`<details>` Xem dạng bang) để mọi giá trị đọc được không cần rê chuột, và tooltip `<title>` trên từng mark.
- Header ghi rõ time range thực tế, nguồn file, số record — đúng yêu cầu "screenshot phải nhìn được tên panel và khoảng thời gian".

### Cách đọc dashboard khi có sự cố

1. KPI row ở trên cùng đổi chip sang **Vuot nguong** → biết ngay SLI nào vỡ.
2. Mở panel tương ứng, đọc phút bị lệch trong table view.
3. Lấy `correlation_id` của request trong phút đó từ `data/logs.jsonl` → mở trace tương ứng trên Langfuse.
