import time
import numpy as np
from voiceprint_manager import voiceprintManager

def test_full_voiceprint_flow():
    print("=== KIỂM THỬ MODULE VOICEPRINT MANAGER ===")
    assert voiceprintManager.is_ready, "VoiceprintManager phải ở trạng thái sẵn sàng!"
    print(f"1. Khởi tạo thành công: Model={voiceprintManager.model_path}, Dim={voiceprintManager.dim}")

    # Tạo 2 mẫu âm thanh PCM 16kHz mono giả lập
    t = np.linspace(0, 2.5, int(16000 * 2.5), dtype=np.float32)
    # Giọng A: Tổ hợp tần số 250Hz, 500Hz, 1000Hz
    voice_a_floats = 0.4 * np.sin(2 * np.pi * 250 * t) + 0.3 * np.sin(2 * np.pi * 500 * t) + 0.2 * np.sin(2 * np.pi * 1000 * t)
    pcm_a = (voice_a_floats * 32767.0).astype(np.int16).tobytes()

    # Giọng B: Tổ hợp tần số 400Hz, 800Hz, 1600Hz
    voice_b_floats = 0.4 * np.sin(2 * np.pi * 400 * t) + 0.3 * np.sin(2 * np.pi * 800 * t) + 0.2 * np.sin(2 * np.pi * 1600 * t)
    pcm_b = (voice_b_floats * 32767.0).astype(np.int16).tobytes()

    # 1. Đăng ký giọng A: "Anh Ty"
    ok, msg = voiceprintManager.enroll("Anh Ty", pcm_a)
    print(f"2. Đăng ký 'Anh Ty': {ok} - {msg}")
    assert ok, "Đăng ký giọng Anh Ty phải thành công"

    # 2. Đăng ký giọng B: "Me"
    ok_b, msg_b = voiceprintManager.enroll("Me", pcm_b)
    print(f"3. Đăng ký 'Me': {ok_b} - {msg_b}")
    assert ok_b, "Đăng ký giọng Me phải thành công"

    # 3. Danh sách hồ sơ
    speakers = voiceprintManager.list_speakers()
    print("4. Danh sách hồ sơ:", [s["name"] for s in speakers])
    assert any(s["name"] == "Anh Ty" for s in speakers), "Phải có Anh Ty trong danh sách"
    assert any(s["name"] == "Me" for s in speakers), "Phải có Me trong danh sách"

    # 4. Thử nhận diện đoạn âm thanh A kèm nhiễu
    noisy_a_floats = voice_a_floats + np.random.normal(0, 0.05, len(voice_a_floats)).astype(np.float32)
    pcm_test_a = (noisy_a_floats * 32767.0).astype(np.int16).tobytes()

    t_start = time.time()
    speaker, score, all_scores = voiceprintManager.identify(pcm_test_a, threshold=0.50)
    elapsed = (time.time() - t_start) * 1000
    print(f"5. Nhận diện giọng Anh Ty: '{speaker}' (Điểm: {score:.3f}, Thời gian: {elapsed:.1f}ms, Bảng điểm: {all_scores})")
    assert speaker == "Anh Ty", f"Phải nhận diện ra Anh Ty, kết quả: {speaker}"

    # 5. Dọn dẹp mẫu thử
    voiceprintManager.delete("Anh Ty")
    voiceprintManager.delete("Me")
    print("6. Đã xóa hồ sơ thử nghiệm sạch sẽ!")
    print("=== TẤT CẢ KIỂM THỬ ĐẠT PASS 100%! ===")

if __name__ == "__main__":
    test_full_voiceprint_flow()
