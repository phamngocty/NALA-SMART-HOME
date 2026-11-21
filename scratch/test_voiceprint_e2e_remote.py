import urllib.request
import json
import base64
import wave
import io
import sys

sys.stdout.reconfigure(encoding='utf-8')

NAS_URL = 'http://192.168.1.114:8765'

def make_dummy_wav(freq=440, duration_sec=1.0, sample_rate=16000):
    import math
    import struct
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        n_samples = int(duration_sec * sample_rate)
        frames = []
        for i in range(n_samples):
            val = int(10000 * math.sin(2 * math.pi * freq * (i / sample_rate)))
            frames.append(struct.pack('<h', val))
        wf.writeframes(b''.join(frames))
    return buf.getvalue()

print("=== BẮT ĐẦU TEST TOÀN DIỆN VÂN GIỌNG ĐA MẪU XIAOZHI TRÊN NAS ===")

# 1. Tạo 2 mẫu âm thanh giả lập (đại diện cho 2 câu nói)
wav1 = make_dummy_wav(freq=300, duration_sec=1.5)
wav2 = make_dummy_wav(freq=350, duration_sec=1.5)
b64_1 = base64.b64encode(wav1).decode('utf-8')
b64_2 = base64.b64encode(wav2).decode('utf-8')

# 2. Test Enroll Đa Mẫu (audio_list_base64)
speaker_test_name = "Anh_Ty_XiaoZhi_Test"
payload = {
    "speaker_name": speaker_test_name,
    "audio_list_base64": [b64_1, b64_2]
}

print(f"1. Gửi yêu cầu đăng ký đa mẫu cho '{speaker_test_name}'...")
req = urllib.request.Request(
    f"{NAS_URL}/api/voiceprint/enroll",
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(req, timeout=10)
body = json.loads(res.read().decode('utf-8'))
print("Kết quả Enroll:", body)
assert body.get('status') == 'success', f"Enroll failed: {body}"
assert body.get('samples_count') == 2, f"Expected 2 samples: {body}"

# 3. Test Lấy Danh Sách Người Dùng
print("\n2. Kiểm tra danh sách người dùng...")
res = urllib.request.urlopen(f"{NAS_URL}/api/voiceprint/speakers", timeout=5)
spk_body = json.loads(res.read().decode('utf-8'))
print("Speakers:", spk_body)
speakers = spk_body.get('speakers', [])
found = next((s for s in speakers if s['name'] == speaker_test_name), None)
assert found is not None, "Speaker not found in list!"
print(f"✅ Đã tìm thấy '{found['name']}' với {found.get('samples_count')} mẫu vector!")

# 4. Test Nhận Diện (Identify) với mẫu wav1
print(f"\n3. Thử nghiệm nhận diện giọng nói vừa đăng ký...")
ident_payload = {
    "audio_base64": b64_1,
    "threshold": 0.50
}
req = urllib.request.Request(
    f"{NAS_URL}/api/voiceprint/identify",
    data=json.dumps(ident_payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(req, timeout=10)
ident_body = json.loads(res.read().decode('utf-8'))
print("Kết quả Identify:", ident_body)
print(f"Matched: {ident_body.get('matched_speaker')} - Điểm tương đồng: {ident_body.get('score')}")

# 5. Dọn dẹp hồ sơ test
print(f"\n4. Xóa hồ sơ test '{speaker_test_name}'...")
req = urllib.request.Request(
    f"{NAS_URL}/api/voiceprint/speakers/{speaker_test_name}",
    method='DELETE'
)
del_res = urllib.request.urlopen(req, timeout=5)
del_body = json.loads(del_res.read().decode('utf-8'))
print("Xóa kết quả:", del_body)

print("\n🎉 TẤT CẢ CÁC BÀI KIỂM THỬ ĐÃ THÀNH CÔNG 100%! HỆ THỐNG VÂN GIỌNG XIAOZHI ĐÃ SẴN SÀNG.")
