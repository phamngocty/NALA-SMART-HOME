import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

filepath = 'server_nas_hub/app/ai_agent_router.py'
with open(filepath, 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update _load_initial_config
old_cfg_anchor = '''            "openrouter": {
                "api_key": os.getenv("OPENROUTER_API_KEY", ""),
                "model": "google/gemini-2.0-flash-exp:free",
                "base_url": "https://openrouter.ai/api/v1"
            },'''

new_cfg_anchor = '''            "openrouter": {
                "api_key": os.getenv("OPENROUTER_API_KEY", ""),
                "model": "qwen/qwen-2.5-72b-instruct:free",
                "base_url": "https://openrouter.ai/api/v1"
            },
            "siliconflow": {
                "api_key": os.getenv("SILICONFLOW_API_KEY", ""),
                "model": "Qwen/Qwen2.5-7B-Instruct",
                "base_url": "https://api.siliconflow.cn/v1"
            },'''

assert old_cfg_anchor in code, "Could not find old_cfg_anchor in _load_initial_config"
code = code.replace(old_cfg_anchor, new_cfg_anchor, 1)

# 2. Update get_safe_config
old_safe_anchor = '''            "openrouter": {
                "api_key_masked": mask_key(self.config["openrouter"].get("api_key")),
                "has_key": bool(self.config["openrouter"].get("api_key")),
                "model": self.config["openrouter"].get("model", "google/gemini-2.0-flash-exp:free"),
                "base_url": self.config["openrouter"].get("base_url", "https://openrouter.ai/api/v1")
            },'''

new_safe_anchor = '''            "openrouter": {
                "api_key_masked": mask_key(self.config.get("openrouter", {}).get("api_key")),
                "has_key": bool(self.config.get("openrouter", {}).get("api_key")),
                "model": self.config.get("openrouter", {}).get("model", "qwen/qwen-2.5-72b-instruct:free"),
                "base_url": self.config.get("openrouter", {}).get("base_url", "https://openrouter.ai/api/v1")
            },
            "siliconflow": {
                "api_key_masked": mask_key(self.config.get("siliconflow", {}).get("api_key")),
                "has_key": bool(self.config.get("siliconflow", {}).get("api_key")),
                "model": self.config.get("siliconflow", {}).get("model", "Qwen/Qwen2.5-7B-Instruct"),
                "base_url": self.config.get("siliconflow", {}).get("base_url", "https://api.siliconflow.cn/v1")
            },'''

assert old_safe_anchor in code, "Could not find old_safe_anchor in get_safe_config"
code = code.replace(old_safe_anchor, new_safe_anchor, 1)

# 3. Update save_config providers loop
code = code.replace(
    'for prov in ["gemini", "deepseek", "groq", "openrouter", "custom"]:',
    'for prov in ["gemini", "deepseek", "groq", "openrouter", "siliconflow", "custom"]:'
)

# 4. Update list_available_models defaults
old_openrouter_defaults = '''        default_openrouter = [
            {"id": "google/gemini-2.0-flash-exp:free", "name": "google/gemini-2.0-flash-exp:free [Miễn phí]"},
            {"id": "deepseek/deepseek-chat", "name": "deepseek/deepseek-chat (DeepSeek V3)"},
            {"id": "meta-llama/llama-3.3-70b-instruct", "name": "meta-llama/llama-3.3-70b-instruct"}
        ]'''

new_openrouter_defaults = '''        default_openrouter = [
            {"id": "qwen/qwen-2.5-72b-instruct:free", "name": "qwen/qwen-2.5-72b-instruct:free [Miễn phí · Qwen 72B]"},
            {"id": "deepseek/deepseek-r1:free", "name": "deepseek/deepseek-r1:free [Miễn phí · Suy luận R1]"},
            {"id": "google/gemini-2.0-flash-exp:free", "name": "google/gemini-2.0-flash-exp:free [Miễn phí · Google Flash]"},
            {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "meta-llama/llama-3.3-70b-instruct:free [Miễn phí · Llama 70B]"},
            {"id": "deepseek/deepseek-chat", "name": "deepseek/deepseek-chat (DeepSeek V3 Chính thức)"},
            {"id": "meta-llama/llama-3.3-70b-instruct", "name": "meta-llama/llama-3.3-70b-instruct"}
        ]

        default_siliconflow = [
            {"id": "Qwen/Qwen2.5-7B-Instruct", "name": "Qwen/Qwen2.5-7B-Instruct [Miễn phí 100% · Siêu tốc]"},
            {"id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B", "name": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B [Miễn phí 100% · Suy luận R1]"},
            {"id": "Qwen/Qwen2.5-Coder-7B-Instruct", "name": "Qwen/Qwen2.5-Coder-7B-Instruct [Miễn phí 100% · Coder]"},
            {"id": "THUDM/glm-4-9b-chat", "name": "THUDM/glm-4-9b-chat [Miễn phí 100% · GLM-4]"},
            {"id": "internlm/internlm2_5-7b-chat", "name": "internlm/internlm2_5-7b-chat [Miễn phí 100%]"},
            {"id": "Qwen/Qwen2.5-32B-Instruct", "name": "Qwen/Qwen2.5-32B-Instruct (Qwen 32B Cân bằng cao cấp)"},
            {"id": "Qwen/Qwen2.5-72B-Instruct", "name": "Qwen/Qwen2.5-72B-Instruct (Qwen 72B Đỉnh cao ngôn ngữ)"},
            {"id": "deepseek-ai/DeepSeek-V3", "name": "deepseek-ai/DeepSeek-V3 (DeepSeek V3 Đàm thoại xuất sắc)"},
            {"id": "deepseek-ai/DeepSeek-R1", "name": "deepseek-ai/DeepSeek-R1 (DeepSeek R1 Suy luận sâu)"},
            {"id": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B", "name": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B (R1 Llama 70B)"}
        ]'''

assert old_openrouter_defaults in code, "Could not find old_openrouter_defaults"
code = code.replace(old_openrouter_defaults, new_openrouter_defaults, 1)

# 5. Add siliconflow live model scan in list_available_models
old_scan_anchor = '''                # 4. OPENROUTER
                elif provider == "openrouter":'''

new_scan_anchor = '''                # 4. SILICONCLOUD (SILICONFLOW - XIAOZHI BACKEND)
                elif provider == "siliconflow":
                    if key:
                        try:
                            endpoint = "https://api.siliconflow.cn/v1/models"
                            headers = {"Authorization": f"Bearer {key}"}
                            res = await client.get(endpoint, headers=headers)
                            if res.status_code == 200:
                                data = res.json()
                                for m in data.get("data", []):
                                    m_id = m.get("id", "")
                                    if any(ign in m_id.lower() for ign in ["embedding", "rerank", "bge", "tts", "stt", "whisper", "flux", "stable-diffusion"]):
                                        continue
                                    desc = ""
                                    if any(f in m_id for f in ["Qwen2.5-7B", "Distill-Qwen-7B", "glm-4-9b", "internlm2_5-7b"]):
                                        desc = " [Miễn phí 100%]"
                                    elif "Qwen2.5-72B" in m_id:
                                        desc = " (Qwen 72B Đỉnh cao)"
                                    elif "DeepSeek-V3" in m_id:
                                        desc = " (DeepSeek V3)"
                                    elif "DeepSeek-R1" in m_id:
                                        desc = " (DeepSeek R1)"
                                    models.append({"id": m_id, "name": f"{m_id}{desc}"})
                        except Exception as e:
                            logger.warning("SiliconFlow live scan failed (%s), using defaults", e)
                    if not models:
                        return default_siliconflow
                    existing = {m["id"] for m in models}
                    ordered = [m for m in default_siliconflow if m["id"] in existing]
                    for m in models:
                        if m["id"] not in {x["id"] for x in ordered}:
                            ordered.append(m)
                    return ordered

                # 5. OPENROUTER
                elif provider == "openrouter":'''

assert old_scan_anchor in code, "Could not find old_scan_anchor in list_available_models"
code = code.replace(old_scan_anchor, new_scan_anchor, 1)

# In fallback exception in list_available_models
code = code.replace(
    'elif provider == "openrouter":\n                return default_openrouter',
    'elif provider == "openrouter":\n                return default_openrouter\n            elif provider == "siliconflow":\n                return default_siliconflow'
)

# 6. Add siliconflow to test_connection
old_test_anchor = '''                # 4. OPENROUTER (9 Router) API (openrouter.ai/api/v1/chat/completions)
                elif provider == "openrouter":'''

new_test_anchor = '''                # 4. SILICONCLOUD (SILICONFLOW - XIAOZHI BACKEND)
                elif provider == "siliconflow":
                    norm_mod = mod or "Qwen/Qwen2.5-7B-Instruct"
                    base = url or "https://api.siliconflow.cn/v1"
                    endpoint = f"{base.rstrip('/')}/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": norm_mod,
                        "messages": [
                            {"role": "user", "content": "Trả lời 'OK' nếu bạn nhận được tin này."}
                        ],
                        "max_tokens": 10,
                        "temperature": 0.2
                    }
                    res = await client.post(endpoint, headers=headers, json=payload)
                    elapsed = int((time.time() - t0) * 1000)
                    if res.status_code == 200:
                        data = res.json()
                        reply = data["choices"][0]["message"]["content"].strip()
                        return {"status": "success", "latency_ms": elapsed, "reply": reply, "model": norm_mod, "provider": provider}
                    elif res.status_code == 401:
                        return {"status": "error", "http_code": 401, "message": "API Key SiliconCloud (sk-...) không hợp lệ. Vui lòng lấy key tại cloud.siliconflow.cn/account/ak", "latency_ms": elapsed}
                    else:
                        return {"status": "error", "http_code": res.status_code, "message": res.text[:250], "latency_ms": elapsed}

                # 5. OPENROUTER (9 Router) API (openrouter.ai/api/v1/chat/completions)
                elif provider == "openrouter":'''

assert old_test_anchor in code, "Could not find old_test_anchor in test_connection"
code = code.replace(old_test_anchor, new_test_anchor, 1)

# 7. Add siliconflow in process_intent
old_pi_anchor = '''                        elif prov == "openrouter":
                            endpoint = "https://openrouter.ai/api/v1/chat/completions"
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                                "HTTP-Referer": "https://nalasmarthome.local",
                                "X-Title": "NALA Smart Home Hub"
                            }
                            use_model = model or "google/gemini-2.0-flash-exp:free"'''

new_pi_anchor = '''                        elif prov == "openrouter":
                            endpoint = "https://openrouter.ai/api/v1/chat/completions"
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                                "HTTP-Referer": "https://nalasmarthome.local",
                                "X-Title": "NALA Smart Home Hub"
                            }
                            use_model = model or "qwen/qwen-2.5-72b-instruct:free"
                        elif prov == "siliconflow":
                            base = base_url or "https://api.siliconflow.cn/v1"
                            endpoint = f"{base.rstrip('/')}/chat/completions"
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            }
                            use_model = model or "Qwen/Qwen2.5-7B-Instruct"'''

assert old_pi_anchor in code, "Could not find old_pi_anchor in process_intent"
code = code.replace(old_pi_anchor, new_pi_anchor, 1)

# 8. Add siliconflow in stream_intent
old_si_anchor = '''                        elif prov == "openrouter":
                            endpoint = "https://openrouter.ai/api/v1/chat/completions"
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                                "HTTP-Referer": "https://nalasmarthome.local",
                                "X-Title": "NALA Smart Home Hub"
                            }
                            use_model = model or "google/gemini-2.0-flash-exp:free"'''

new_si_anchor = '''                        elif prov == "openrouter":
                            endpoint = "https://openrouter.ai/api/v1/chat/completions"
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                                "HTTP-Referer": "https://nalasmarthome.local",
                                "X-Title": "NALA Smart Home Hub"
                            }
                            use_model = model or "qwen/qwen-2.5-72b-instruct:free"
                        elif prov == "siliconflow":
                            base = base_url or "https://api.siliconflow.cn/v1"
                            endpoint = f"{base.rstrip('/')}/chat/completions"
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            }
                            use_model = model or "Qwen/Qwen2.5-7B-Instruct"'''

assert old_si_anchor in code, "Could not find old_si_anchor in stream_intent"
code = code.replace(old_si_anchor, new_si_anchor, 1)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(code)

print("✅ Successfully updated ai_agent_router.py with SiliconCloud (SiliconFlow) backend support!")
