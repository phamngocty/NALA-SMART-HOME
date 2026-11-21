import sherpa_onnx
import numpy as np

config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
    model="/app/app/models/campplus_model.onnx",
    num_threads=2,
    provider="cpu",
    debug=False
)
extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
manager = sherpa_onnx.SpeakerEmbeddingManager(extractor.dim)

t = np.linspace(0, 2.0, 32000, dtype=np.float32)
audio_a = (0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
audio_b = (0.5 * np.sin(2 * np.pi * 1200 * t)).astype(np.float32)

s_a = extractor.create_stream()
s_a.accept_waveform(16000, audio_a)
s_a.input_finished()
emb_a = extractor.compute(s_a)

s_b = extractor.create_stream()
s_b.accept_waveform(16000, audio_b)
s_b.input_finished()
emb_b = extractor.compute(s_b)

manager.add("Person_A", emb_a)
manager.add("Person_B", emb_b)

print("Score(Person_A, emb_a):", manager.score("Person_A", emb_a))
print("Score(Person_B, emb_a):", manager.score("Person_B", emb_a))
print("Score(Person_B, emb_b):", manager.score("Person_B", emb_b))
print("Score(Person_A, emb_b):", manager.score("Person_A", emb_b))
print("All speakers:", manager.all_speakers)
