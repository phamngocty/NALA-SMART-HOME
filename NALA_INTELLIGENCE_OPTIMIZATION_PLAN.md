# 🚀 KẾ HOẠCH PHÁT TRIỂN & TỐI ƯU TOÀN DIỆN TRỢ LÝ NALA SMART HOME
> **Tài liệu chiến lược**: Nâng cao trí thông minh (Intelligence), Tốc độ phản hồi siêu tốc (Sub-second Latency) và Độ chính xác tuyệt đối (Deterministic Accuracy).  
> **Phiên bản**: v1.0.0 | **Ngày lưu trữ**: 10/11/2026 | **Hệ thống**: NALA Smart Home Ecosystem

---

## 🎯 I. MỤC TIÊU CỐT LÕI (CORE GOALS)
1. **Tốc độ phản xạ (Sub-second Latency)**: Rút ngắn thời gian từ lúc dứt lời đến khi loa phát tiếng từ ~2.5s xuống **dưới 0.8s** (đối với lệnh thông dụng: **< 0.15s**).
2. **Độ chính xác tuyệt đối (Zero Hallucination & 100% Room-Awareness)**: Không bao giờ nhầm phòng; không bao giờ bịa mã thiết bị Home Assistant (`entity_id`).
3. **Trí thông minh tự nhiên (Deep Context & Indirect Intent)**: Hiểu những điều người dùng không nói thẳng ra (*"Nóng quá"*, *"Tối thế"*, *"Tôi đi ngủ"*); nhớ ngữ cảnh câu trước để trò chuyện liên tục.

---

## 🏛️ II. KIẾN TRÚC TỐI ƯU HÓA 3 TRỤ CỘT

```
[Giọng Nói Người Dùng]
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. TỐI ƯU TỐC ĐỘ (Sub-Second Latency)                       │
│ - VAD Silence Timeout: 800ms ➔ 380ms - 450ms                │
│ - Groq Whisper STT + Prompt Bias: ~120ms - 150ms            │
│ - Local Fast-Path Semantic Intent: < 20ms (Bỏ qua LLM)       │
│ - Pre-warmed Audio Fillers ("Dạ,", Chime): Loa kêu sau 40ms │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. ĐỘ CHÍNH XÁC (Zero Hallucination)                        │
│ - Scoped Room Entities: Chỉ nạp thiết bị phòng của Panel    │
│ - Whisper Vocabulary Bias: Ép chuẩn từ vựng tiếng Việt      │
│ - Fuzzy Entity Matching: Tự sửa lỗi chính tả trước khi gọi  │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. TRÍ THÔNG MINH NGỮ CẢNH (Deep Intelligence)              │
│ - Indirect Intent Mapping: Hiểu câu gián tiếp / cảm xúc     │
│ - Multi-turn Context Memory: Nhớ câu lệnh trước đó          │
│ - Adaptive Learned Memory: Tự nhớ thói quen & biệt danh     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📅 III. LỘ TRÌNH 4 GIAI ĐOẠN TRIỂN KHAI (ACTIONABLE ROADMAP)

### 🔹 Giai đoạn 1: STT Prompt Bias + Fast-Path Semantic Engine
- **Mục tiêu**: Tối ưu tốc độ cho 80% câu lệnh thường dùng hàng ngày, giảm độ trễ xuống **< 0.5s**.
- **Nội dung kỹ thuật**:
  - [ ] **Ghim từ điển Smart Home vào Groq Whisper**:
    - Truyền `prompt="Nala ơi, đèn hắt, đèn chùm, downlight, quạt trần, điều hòa, máy lạnh, rèm cửa, phòng khách, phòng ngủ, bật, tắt, mở, đóng"` vào API `/v1/audio/transcriptions`.
    - Loại bỏ 100% tình trạng nghe nhầm tên thiết bị tiếng Việt.
  - [ ] **Mở rộng bộ khớp lệnh nhanh (Local Fast-Path Matching)**:
    - Nhận diện các câu điều khiển thông dụng (Bật/tắt/mở/đóng + thiết bị + phòng) xử lý trực tiếp qua `ha_bridge` mà không tốn thời gian gọi lên LLM.
  - [ ] **Nâng cấp âm thanh đệm (Pre-warmed Audio Fillers)**:
    - Bổ sung các mẫu xác nhận tự nhiên vào RAM Cache: *"Dạ vâng"*, *"Em làm ngay"*, *"Đã chỉnh xong"*.
- **Kết quả nghiệm thu**: Lệnh bật/tắt thiết bị phản hồi ngay trong vòng 80ms - 150ms.

---

### 🔹 Giai đoạn 2: Định Vị Không Gian Tuyệt Đối (Scoped Room Context) & Chống Ảo Giác
- **Mục tiêu**: Nala hiểu chính xác 100% thiết bị cần điều khiển dựa vào vị trí của màn hình gắn tường đang nhận lệnh.
- **Nội dung kỹ thuật**:
  - [ ] **Khoanh vùng thiết bị theo phòng (Scoped Entities)**:
    - Khi nhận lệnh từ panel phòng nào (ví dụ: *Phòng Ngủ Master*), server chỉ đưa các thiết bị của phòng đó lên đầu danh sách prompt của LLM.
    - Người dùng chỉ cần nói *"Bật đèn"*, Nala tự động bật đèn phòng ngủ master mà không bao giờ hỏi lại hay nhầm phòng khách.
  - [ ] **Bộ kiểm tra đối chiếu thực thể (Fuzzy Entity Validator)**:
    - Trước khi gửi lệnh sang Home Assistant qua WebSocket, server đối chiếu `entity_id` với cơ sở dữ liệu thực tế.
    - Nếu LLM sinh sai ký tự (ảo giác), tự động sửa lỗi chính tả bằng thuật toán so khớp mờ (Levenshtein).
- **Kết quả nghiệm thu**: Tỉ lệ điều khiển đúng phòng và đúng thiết bị đạt 100%.

---

### 🔹 Giai đoạn 3: Động Cơ Suy Luận Ngôn Ngữ Gián Tiếp & Nhớ Ngữ Cảnh Đa Lượt
- **Mục tiêu**: Giúp Nala hiểu cảm xúc, thói quen và duy trì cuộc trò chuyện tự nhiên như người thật.
- **Nội dung kỹ thuật**:
  - [ ] **Indirect Intent Engine (Hiểu câu nói gián tiếp)**:
    - *"Nóng nực quá"* $\rightarrow$ Tự kiểm tra nhiệt độ phòng hiện tại; nếu điều hòa chưa bật thì bật 24°C, nếu đang bật thì giảm 1-2°C.
    - *"Phòng tối thế"* $\rightarrow$ Bật đèn chiếu sáng chính của phòng.
    - *"Buồn ngủ rồi / Chuẩn bị đi ngủ"* $\rightarrow$ Tắt đèn trần, bật đèn ngủ vàng ấm 15%, chỉnh điều hòa 26°C, kéo rèm lại.
    - *"Tôi chuẩn bị đi làm / ra ngoài"* $\rightarrow$ Kích hoạt kịch bản ra khỏi nhà (Tắt toàn bộ thiết bị, kiểm tra khóa cửa).
  - [ ] **Kế thừa ngữ cảnh nhiều lượt (Multi-turn Context Memory)**:
    - Câu 1: *"Bật điều hòa phòng làm việc"* $\rightarrow$ Nala: *"Dạ, em đã bật điều hòa phòng làm việc 25 độ."*
    - Câu 2: *"Cho lạnh hơn chút nữa"* $\rightarrow$ Nala tự hiểu giảm điều hòa phòng làm việc xuống 23°C (không hỏi lại tên thiết bị).
    - Câu 3: *"Cả quạt nữa nhé"* $\rightarrow$ Nala tự hiểu bật luôn quạt phòng làm việc.
  - [ ] **Khai thác Trí Nhớ Học Hỏi (Adaptive Memory)**:
    - Tự động áp dụng biệt danh và thói quen theo khung giờ (sáng/chiều/tối/đêm) vào ngữ cảnh prompt.
- **Kết quả nghiệm thu**: Trò chuyện tự nhiên, liên tục không cần gọi lại từ khóa đánh thức nhiều lần.

---

### 🔹 Giai đoạn 4: Tinh Chỉnh Firmware ESP32 VAD Nhả Mic Tức Thì
- **Mục tiêu**: Tối ưu lớp phần cứng mic thu âm trên panel gắn tường.
- **Nội dung kỹ thuật**:
  - [ ] **Điều chỉnh Silero VAD / Silence Hangover**:
    - Giảm thời gian chờ im lặng từ 800ms xuống **380ms - 450ms** khi phát hiện câu nói ngắn.
    - Khi người dùng vừa ngắt tiếng, ESP32 ngắt thu và gửi tín hiệu kết thúc ngay lập tức.
  - [ ] **Cập nhật OTA không dây**:
    - Đóng gói firmware mới và đẩy tự động xuống các màn hình qua chức năng OTA của NAS Hub.
- **Kết quả nghiệm thu**: Tổng độ trễ toàn trình (End-to-End) từ lúc người dùng dứt lời đến khi thiết bị nhảy trạng thái đạt **dưới 0.8 giây**.

---

## 📌 IV. HƯỚNG DẪN KÍCH HOẠT KHI BẠN SẴN SÀNG

Khi bạn muốn bắt đầu triển khai bất kỳ giai đoạn nào, chỉ cần đưa ra yêu cầu ngắn gọn:

- **Triển khai toàn bộ**: *"Bắt đầu triển khai kế hoạch tối ưu Nala"*
- **Triển khai từng giai đoạn**:
  - *"Triển khai Giai đoạn 1: STT Prompt Bias và Fast-Path"*
  - *"Triển khai Giai đoạn 2: Scoped Room Context và Fuzzy Matching"*
  - *"Triển khai Giai đoạn 3: Indirect Intent Engine và Multi-turn Context"*
  - *"Triển khai Giai đoạn 4: Tối ưu VAD nhả mic nhanh trên Firmware ESP32"*

---
*Tài liệu đã được lưu trữ vĩnh viễn trên hệ thống máy chủ NAS Hub và Workspace dự án.*
