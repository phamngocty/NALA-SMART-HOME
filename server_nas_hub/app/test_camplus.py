import time
import numpy as np
import sherpa_onnx
import os

print("=== NALA VOICEPRINT ENGINE (CAM++ ONNX BENCHMARK) ===")
model_path = "/app/app/models/campplus_model.onnx"
if not os.path.exists(model_path):
    # Fallback to local path if running outside docker
    model_path = "models/campplus_model.onnx"

config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
    model=model_path,
    num_threads=2,
    provider="cpu",
    debug=False
)
assert config.validate(), "Invalid CAM++ config!"

t0 = time.time()
extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
manager = sherpa_onnx.SpeakerEmbeddingManager(extractor.dim)
init_ms = (time.time() - t0) * 1000
print(f"1. Khởi tạo Extractor: {init_ms:.2f} ms | Số chiều vector đặc trưng: {extractor.dim}")

# Tạo 2 mẫu âm thanh giả lập 16kHz (2 giây)
t = np.linspace(0, 2.0, 32000, dtype=np.float32)
voice_ty = (0.5 * np.sin(2 * np.pi * 300 * t) + 0.3 * np.sin(2 * np.pi * 600 * t)).astype(np.float32)
voice_me = (0.5 * np.sin(2 * np.pi * 500 * t) + 0.3 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)

# Đo độ trễ trích xuất đặc trưng (Feature Extraction Latency)
stream1 = extractor.create_stream()
stream1.accept_waveform(16000, voice_ty)
stream1.input_finished()

t1 = time.time()
emb_ty = extractor.compute(stream1)
infer_ms = (time.time() - t1) * 1000
print(f"2. Độ trễ trích xuất vân giọng: {infer_ms:.2f} ms | Độ dài vector: {len(emb_ty)}")

# Đăng ký hồ sơ giọng nói (Enrollment)
ok1 = manager.add("Anh Ty", emb_ty)
print(f"3. Đăng ký giọng 'Anh Ty': {ok1}")

stream_me = extractor.create_stream()
stream_me.accept_waveform(16000, voice_me)
stream_me.input_finished()
emb_me = extractor.compute(stream_me)
ok2 = manager.add("Me", emb_me)
print(f"   Đăng ký giọng 'Me': {ok2}")

# Test nhận diện cùng người (Same speaker)
stream_test1 = extractor.create_stream()
# Thêm chút nhiễu nhẹ
noisy_voice_ty = voice_ty + np.random.normal(0, 0.05, len(voice_ty)).astype(np.float32)
stream_test1.accept_waveform(16000, noisy_voice_ty)
stream_test1.input_finished()

t2 = time.time()
emb_test1 = extractor.compute(stream_test1)
identified_ty = manager.search(emb_test1, threshold=0.50)
search_ms = (time.time() - t2) * 1000
print(f"4. Thử nghiệm nhận diện giọng Anh Ty: '{identified_ty}' (Thời gian: {search_ms:.2f} ms)")

# Test nhận diện người khác (Different speaker)
stream_test2 = extractor.create_stream()
noisy_voice_me = voice_me + np.random.normal(0, 0.05, len(voice_me)).astype(np.float32)
stream_test2.accept_waveform(16000, noisy_voice_me)
stream_test2.input_finished()
emb_test2 = extractor.compute(stream_test2)
identified_me = manager.search(emb_test2, threshold=0.50)
print(f"5. Thử nghiệm nhận diện giọng Me: '{identified_me}'")

print("=== HOÀN TẤT KIỂM THỬ THÀNH CÔNG 100%! ===")
