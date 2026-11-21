import urllib.request
import os

test_files = [
    ("speaker1_sample1.wav", "https://github.com/k2-fsa/sherpa-onnx/raw/master/python-api-examples/test_data/speaker1_sample1.wav"),
    ("speaker1_sample2.wav", "https://github.com/k2-fsa/sherpa-onnx/raw/master/python-api-examples/test_data/speaker1_sample2.wav"),
    ("speaker2_sample1.wav", "https://github.com/k2-fsa/sherpa-onnx/raw/master/python-api-examples/test_data/speaker2_sample1.wav")
]

os.makedirs("scratch/test_audio", exist_ok=True)
for fname, url in test_files:
    out_path = os.path.join("scratch/test_audio", fname)
    if not os.path.exists(out_path):
        print(f"Downloading {fname}...")
        try:
            urllib.request.urlretrieve(url, out_path)
            print(f"Saved {out_path} ({os.path.getsize(out_path)} bytes)")
        except Exception as e:
            print(f"Failed to download {fname}: {e}")
