import urllib.request
import json

url = "https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/speaker-recongition-models"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        campplus_assets = [a for a in data.get("assets", []) if "campplus" in a["name"] or "3d" in a["name"]]
        for a in campplus_assets:
            print(f"- {a['name']} ({a['size'] / 1024 / 1024:.1f} MB): {a['browser_download_url']}")
except Exception as e:
    print("Error:", e)
