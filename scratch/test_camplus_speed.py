import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)

test_code = """
import time
import numpy as np
import sherpa_onnx

print("Testing SpeakerEmbeddingExtractor...")
config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
    model="/app/app/models/campplus_model.onnx",
    num_threads=2,
    provider="cpu",
    debug=False
)
assert config.validate(), "Invalid config!"

t0 = time.time()
extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
manager = sherpa_onnx.SpeakerEmbeddingManager(extractor.dim)
init_time = (time.time() - t0) * 1000
print(f"Extractor initialized in {init_time:.2f}ms (dim={extractor.dim})")

# Generate 2 seconds of synthetic 16kHz audio (sine wave 440Hz vs 880Hz)
t = np.linspace(0, 2.0, 32000, dtype=np.float32)
audio1 = 0.5 * np.sin(2 * np.pi * 440 * t)
audio2 = 0.5 * np.sin(2 * np.pi * 880 * t)

# Test embedding computation latency
stream1 = extractor.create_stream()
stream1.accept_waveform(16000, audio1)
stream1.input_finished()

t1 = time.time()
emb1 = extractor.compute(stream1)
infer_time = (time.time() - t1) * 1000
print(f"Inference latency: {infer_time:.2f}ms! Vector shape: {len(emb1)}")

# Register speaker 'Anh Ty'
success = manager.add("Anh Ty", emb1)
print(f"Registered 'Anh Ty': {success}")

# Search with exact same audio
stream_test = extractor.create_stream()
stream_test.accept_waveform(16000, audio1)
stream_test.input_finished()
emb_test = extractor.compute(stream_test)

identified = manager.search(emb_test, threshold=0.60)
print(f"Match result (same voice): '{identified}' (Expected 'Anh Ty')")

# Search with different audio
stream2 = extractor.create_stream()
stream2.accept_waveform(16000, audio2)
stream2.input_finished()
emb2 = extractor.compute(stream2)

diff_identified = manager.search(emb2, threshold=0.60)
print(f"Match result (different voice): '{diff_identified}' (Expected None/empty)")
"""

stdin, stdout, stderr = ssh.exec_command(f'docker exec -w /app nala_nas_ws_hub python3 -c "{test_code}"')
print("STDOUT:\n" + stdout.read().decode())
print("STDERR:\n" + stderr.read().decode())

ssh.close()
