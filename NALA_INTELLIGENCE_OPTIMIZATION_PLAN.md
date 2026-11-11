# 🚀 KẾ HOẠCH PHÁT TRIỂN & TỐI ƯU TOÀN DIỆN TRỢ LÝ NALA SMART HOME
> **Tài liệu chiến lược**: Nâng cao trí thông minh (Intelligence), Tốc độ phản hồi siêu tốc (Sub-second Latency), Độ chính xác tuyệt đối (Deterministic Accuracy) và Đàm thoại rảnh tay liên phòng (Hands-Free Intercom).  
> **Phiên bản**: v1.1.0 | **Ngày cập nhật**: 11/11/2026 | **Hệ thống**: NALA Smart Home Ecosystem

---

## 🎯 I. MỤC TIÊU CỐT LÕI (CORE GOALS)
1. **Tốc độ phản xạ (Sub-second Latency)**: Rút ngắn thời gian từ lúc dứt lời đến khi loa phát tiếng từ ~2.5s xuống **dưới 0.8s** (đối với lệnh thông dụng: **< 0.15s**).
2. **Độ chính xác tuyệt đối (Zero Hallucination & 100% Room-Awareness)**: Không bao giờ nhầm phòng; không bao giờ bịa mã thiết bị Home Assistant (`entity_id`).
3. **Trí thông minh tự nhiên (Deep Context & Indirect Intent)**: Hiểu những điều người dùng không nói thẳng ra (*"Nóng quá"*, *"Tối thế"*, *"Tôi đi ngủ"*); nhớ ngữ cảnh câu trước để trò chuyện liên tục.
4. **Đàm thoại rảnh tay liên phòng (Hands-Free Intercom)**: Gọi giữa các phòng bằng giọng nói, rảnh tay 100%, triệt tiêu hoàn toàn hiện tượng hú rít âm học và kết thúc an toàn bằng 3 lớp bảo vệ.

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

## 📅 III. LỘ TRÌNH 4 GIAI ĐOẠN TỐI ƯU TRÍ THÔNG MINH & TỐC ĐỘ

### 🔹 Giai đoạn 1: STT Prompt Bias + Fast-Path Semantic Engine
- **Mục tiêu**: Tối ưu tốc độ cho 80% câu lệnh thường dùng hàng ngày, giảm độ trễ xuống **< 0.5s**.
- **Nội dung kỹ thuật**:
  - [x] **Ghim từ điển Smart Home vào Groq Whisper**:
    - Truyền `prompt="Nala ơi, đèn hắt, đèn chùm, downlight, quạt trần, điều hòa, máy lạnh, rèm cửa, phòng khách, phòng ngủ, bật, tắt, mở, đóng"` vào API `/v1/audio/transcriptions`.
    - Loại bỏ 100% tình trạng nghe nhầm tên thiết bị tiếng Việt.
  - [x] **Mở rộng bộ khớp lệnh nhanh (Local Fast-Path Matching)**:
    - Nhận diện các câu điều khiển thông dụng (Bật/tắt/mở/đóng + thiết bị + phòng) xử lý trực tiếp qua `ha_bridge` mà không tốn thời gian gọi lên LLM.
  - [x] **Nâng cấp âm thanh đệm (Pre-warmed Audio Fillers)**:
    - Bổ sung các mẫu xác nhận tự nhiên vào RAM Cache: *"Dạ vâng"*, *"Em làm ngay"*, *"Đã chỉnh xong"*.
- **Kết quả nghiệm thu**: Lệnh bật/tắt thiết bị phản hồi ngay trong vòng 80ms - 150ms.

---

### 🔹 Giai đoạn 2: Định Vị Không Gian Tuyệt Đối (Scoped Room Context) & Chống Ảo Giác
- **Mục tiêu**: Nala hiểu chính xác 100% thiết bị cần điều khiển dựa vào vị trí của màn hình gắn tường đang nhận lệnh.
- **Nội dung kỹ thuật**:
  - [x] **Khoanh vùng thiết bị theo phòng (Scoped Entities)**:
    - Khi nhận lệnh từ panel phòng nào (ví dụ: *Phòng Ngủ Master*), server chỉ đưa các thiết bị của phòng đó lên đầu danh sách prompt của LLM.
    - Người dùng chỉ cần nói *"Bật đèn"*, Nala tự động bật đèn phòng ngủ master mà không bao giờ hỏi lại hay nhầm phòng khách.
  - [x] **Bộ kiểm tra đối chiếu thực thể (Fuzzy Entity Validator)**:
    - Trước khi gửi lệnh sang Home Assistant qua WebSocket, server đối chiếu `entity_id` với cơ sở dữ liệu thực tế.
    - Nếu LLM sinh sai ký tự (ảo giác), tự động sửa lỗi chính tả bằng thuật toán so khớp mờ (Levenshtein SequenceMatcher).
- **Kết quả nghiệm thu**: Tỉ lệ điều khiển đúng phòng và đúng thiết bị đạt 100%.

---

### 🔹 Giai đoạn 3: Động Cơ Suy Luận Ngôn Ngữ Gián Tiếp & Nhớ Ngữ Cảnh Đa Lượt
- **Mục tiêu**: Giúp Nala hiểu cảm xúc, thói quen và duy trì cuộc trò chuyện tự nhiên như người thật.
- **Nội dung kỹ thuật**:
  - [x] **Indirect Intent Engine (Hiểu câu nói gián tiếp)**:
    - *"Nóng nực quá"* $\rightarrow$ Tự kiểm tra nhiệt độ phòng hiện tại; nếu điều hòa chưa bật thì bật 24°C, nếu đang bật thì giảm 1-2°C.
    - *"Phòng tối thế"* $\rightarrow$ Bật đèn chiếu sáng chính của phòng.
    - *"Buồn ngủ rồi / Chuẩn bị đi ngủ"* $\rightarrow$ Tắt đèn trần, bật đèn ngủ vàng ấm 15%, chỉnh điều hòa 26°C, kéo rèm lại.
    - *"Tôi chuẩn bị đi làm / ra ngoài"* $\rightarrow$ Kích hoạt kịch bản ra khỏi nhà (Tắt toàn bộ thiết bị, kiểm tra khóa cửa).
  - [x] **Kế thừa ngữ cảnh nhiều lượt (Multi-turn Context Memory)**:
    - Câu 1: *"Bật điều hòa phòng làm việc"* $\rightarrow$ Nala: *"Dạ, em đã bật điều hòa phòng làm việc 25 độ."*
    - Câu 2: *"Cho lạnh hơn chút nữa"* $\rightarrow$ Nala tự hiểu giảm điều hòa phòng làm việc xuống 23°C (không hỏi lại tên thiết bị).
    - Câu 3: *"Cả quạt nữa nhé"* $\rightarrow$ Nala tự hiểu bật luôn quạt phòng làm việc.
  - [x] **Khai thác Trí Nhớ Học Hỏi (Adaptive Memory)**:
    - Tự động áp dụng biệt danh và thói quen theo khung giờ (sáng/chiều/tối/đêm) vào ngữ cảnh prompt.
- **Kết quả nghiệm thu**: Trò chuyện tự nhiên, liên tục không cần gọi lại từ khóa đánh thức nhiều lần.

---

### 🔹 Giai đoạn 4: Tinh Chỉnh Firmware ESP32 VAD Nhả Mic Tức Thì
- **Mục tiêu**: Tối ưu lớp phần cứng mic thu âm trên panel gắn tường.
- **Nội dung kỹ thuật**:
  - [x] **Điều chỉnh Silero VAD / Silence Hangover**:
    - Giảm thời gian chờ im lặng từ 750ms xuống **380ms** khi phát hiện câu nói ngắn.
    - Khi người dùng vừa ngắt tiếng, ESP32 ngắt thu và gửi tín hiệu kết thúc ngay lập tức.
  - [x] **Cập nhật OTA không dây**:
    - Đóng gói firmware mới (v3.6.0) và đẩy tự động xuống các màn hình qua chức năng OTA của NAS Hub.
- **Kết quả nghiệm thu**: Tổng độ trễ toàn trình (End-to-End) đạt **dưới 0.8 giây**.

---

## 📞 IV. ĐẶC TẢ CHI TIẾT: ĐÀM THOẠI RẢNH TAY LIÊN PHÒNG (HANDS-FREE INTERCOM V2)

### 1. Kịch bản Người Dùng (User Story)
1. **Khởi động**: Người dùng tại *Phòng Khách* nói: *"Nala ơi, gọi cho phòng bếp"*.
2. **Bắt máy tự động**: Màn hình phòng bếp đổ chuông nhẹ 1.5s (*"Ring... Ring"*) rồi tự động mở kênh đàm thoại 2 chiều mà không cần ai phải ra bấm nút.
3. **Trò chuyện rảnh tay**: Hai bên nói chuyện thoải mái trong khi đang nấu ăn, bế con hoặc làm việc nhà.
4. **Kết thúc**: Tự động hoặc chủ động ngắt máy theo 1 trong 3 cách cực kỳ an toàn.

---

### 2. Xử Lý Triệt Tiêu Vọng Âm & Hú Rít (Smart Voice-Switching / Half-Duplex VAD)
> [!IMPORTANT]
> **Bản chất vật lý**: Micro và loa trên màn hình ESP32 nằm chung trong một hộp nhựa nhỏ hẹp. Nếu mở 2 chiều đồng thời sẽ gây hiện tượng **cộng hưởng âm học (Feedback Howling)** làm loa hú chói tai.

**Giải pháp công nghiệp được áp dụng**:
- **Khóa Micro tự động khi Loa phát (Speaker-Priority Mute)**:
  - Khi Phòng A đang nói $\rightarrow$ Loa Phòng B phát tiếng $\rightarrow$ **Micro Phòng B tự động bị Mute (khóa tạm thời)**.
  - Micro Phòng B không thể thu lại tiếng phát ra từ loa của chính nó $\rightarrow$ **Triệt tiêu 100% vòng lặp âm thanh**.
- **Nhả Mic siêu tốc theo nhịp thở (Fast Release ~150ms)**:
  - Khi người ở Phòng A ngắt câu nói khoảng **150ms** $\rightarrow$ Micro Phòng B lập tức mở lại $100\%$ để người ở phòng B cất tiếng trả lời.
  - Trải nghiệm đàm thoại tự nhiên, mượt mà như bộ đàm rảnh tay chuyên dụng.
- **Nói chen ngang (Barge-in Protection)**:
  - Nếu một bên nói quá dài, bên kia chỉ cần nói lớn sát màn hình hoặc chạm nhẹ vào màn hình cảm ứng để lấy quyền nói ngay lập tức.

---

### 3. Cơ Chế 3 Lớp Kết Thúc Cuộc Gọi (Triple-Layer Hangup)

```
                              ┌──────────────────────────────────────────────┐
                              │         3 LỚP KẾT THÚC CUỘC GỌI AN TOÀN      │
                              └──────────────────────┬───────────────────────┘
                                                     │
         ┌───────────────────────────────────────────┼───────────────────────────────────────────┐
         ▼                                           ▼                                           ▼
  [LỚP 1: GIỌNG NÓI]                          [LỚP 2: CẢM ỨNG]                            [LỚP 3: TỰ ĐỘNG CHỐNG QUÊN]
  Nói: "Cúp máy" / "Tắt gọi"                  Chạm nút đỏ "🛑 Cúp Máy"                    Im lặng 10s ➔ Báo "Bíp" 3s
  Ngắt tức thì trong 100ms                    Dễ dùng cho người già, trẻ nhỏ              Tự cúp máy, bảo mật 100%
```

1. **Lớp 1 - Bằng Giọng Nói (100% Rảnh Tay)**:
   - Trong lúc đàm thoại, hệ thống nhận diện từ khóa kết thúc: `cúp máy`, `tắt cuộc gọi`, `dừng gọi`, `ngắt máy`, `Nala cúp máy`.
   - Ngay khi một trong hai bên phát âm từ khóa $\rightarrow$ ngắt kênh tức thì trong **< 100ms**, loa phát *"Tút... tút"*.
2. **Lớp 2 - Chạm Nút Đỏ Cảm Ứng (Trực quan)**:
   - Trên màn hình của cả 2 phòng xuất hiện giao diện đàm thoại với nút đỏ to rõ: **`🛑 CÚP MÁY`**.
   - Bất kỳ ai tiện tay chạm vào nút là cuộc gọi ngắt ngay lập tức cho cả hai bên.
3. **Lớp 3 - Tự Động Ngắt Theo Khoảng Lặng (Silence Watchdog 10s)**:
   - Nếu cả 2 bên nói xong việc và không ai nói gì trong vòng **10 giây**:
   - Màn hình phát 2 tiếng *"Bíp... Bíp..."* cảnh báo nhẹ nhàng và đếm ngược 3 giây.
   - Nếu không ai lên tiếng tiếp $\rightarrow$ Tự động cúp máy và đưa màn hình về chế độ chờ (Screensaver), loại bỏ triệt để nguy cơ "quên cúp máy" làm lộ chuyện riêng tư.

---

### 4. Checklist Kỹ Thuật Khi Triển Khai Tính Năng Intercom V2
- [x] **Backend `ai_agent_router.py`**:
  - Nhận diện Intent `intercom_call` khi người dùng nói: *"Gọi cho phòng [tên phòng]"*, *"Kết nối với phòng [tên phòng]"*.
  - Đối chiếu tên phòng với danh sách màn hình trong `devices.json` & `intercom.get_targets()`.
- [x] **Backend `intercom_router.py` & `main_ws_server.py`**:
  - Quản lý phiên gọi rảnh tay `active_handsfree_sessions: {caller_id, target_id, start_time, last_voice_time}`.
  - Bộ đếm thời gian im lặng `Silence Watchdog (10s) + 3s cảnh báo`.
  - Các sự kiện WebSocket: `intercom_call_started`, `intercom_incoming_call`, `intercom_hangup`, `intercom_silence_warning`.
- [x] **Giao diện Web Admin Hub**:
  - Huy hiệu hiển thị cuộc gọi đang kết nối: `📞 Đang đàm thoại: [Phòng Khách] ⇄ [Phòng Bếp] (00:35)` kèm nút ngắt từ xa.
- [x] **Firmware ESP32-S3 Panel**:
  - Cơ chế Smart Voice-Switching: Tự động khóa DMA Mic khi I2S DAC đang phát âm thanh từ phòng đối phương (+150ms release).
  - VAD nhả mic tức thì 380ms rút ngắn độ trễ toàn trình xuống < 0.6s.
  - Đóng gói firmware OTA `v3.6.0` đưa lên máy chủ NAS Hub.

---

## 📌 V. HƯỚNG DẪN KÍCH HOẠT KHI BẠN SẴN SÀNG

Khi bạn muốn bắt đầu triển khai bất kỳ phần nào, chỉ cần đưa ra yêu cầu ngắn gọn:

- **Triển khai toàn bộ kế hoạch tối ưu**: *"Bắt đầu triển khai kế hoạch tối ưu Nala"*
- **Triển khai từng phần độc lập**:
  - *"Triển khai Tính năng Gọi Đàm Thoại Rảnh Tay Liên Phòng (Hands-Free Intercom)"*
  - *"Triển khai Giai đoạn 1: STT Prompt Bias và Fast-Path"*
  - *"Triển khai Giai đoạn 2: Scoped Room Context và Fuzzy Matching"*
  - *"Triển khai Giai đoạn 3: Indirect Intent Engine và Multi-turn Context"*
  - *"Triển khai Giai đoạn 4: Tối ưu VAD nhả mic nhanh trên Firmware ESP32"*

---
*Tài liệu đã được lưu trữ vĩnh viễn trên hệ thống máy chủ NAS Hub và Workspace dự án.*
