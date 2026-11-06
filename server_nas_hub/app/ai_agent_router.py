"""
NALA SMART HOME - ADVANCED AI AGENT ROUTER
Implements official specs:
- Google Gemini: Native Generative Language API (generateContent) with x-goog-api-key & Function Declarations
- DeepSeek: Official OpenAI-compatible Chat Completions API (api.deepseek.com)
- OpenRouter (9 Router): Official OpenRouter API (openrouter.ai/api/v1)
Includes Home Assistant Tool Calling & Room-Context Awareness.
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger("AIRouter")

SYSTEM_PROMPT_TEMPLATE = """Bạn là Nala - Trợ lý giọng nói và quản gia AI của hệ thống NALA Smart Home.
Nhiệm vụ của bạn:
1. Trả lời cực kỳ ngắn gọn, tự nhiên, thân thiện bằng tiếng Việt (tối đa 1-2 câu) để đọc qua loa không bị rườm rà.
2. Điều khiển thiết bị nhà thông minh bằng cách gọi các công cụ (tools) phù hợp khi người dùng yêu cầu bật/tắt thiết bị, điều chỉnh nhiệt độ máy lạnh, tắt hết toàn nhà,...
3. NGỮ CẢNH VỊ TRÍ: Người dùng đang đứng tại phòng: [{current_room}]. Nếu người dùng ra lệnh điều khiển chung chung như 'bật đèn', 'tắt quạt', 'máy lạnh 24 độ' mà không nhắc tên phòng khác, BẮT BUỘC ưu tiên chọn thiết bị thuộc phòng [{current_room}].
4. Nếu người dùng hỏi thông tin bình thường (thời tiết, kiến thức, chào hỏi...), hãy trả lời hóm hỉnh và súc tích.

Danh sách các thiết bị hiện có trong nhà:
{device_context}
"""

def mask_key(k: Optional[str]) -> str:
    if not k:
        return ""
    if len(k) <= 8:
        return "****"
    return f"{k[:4]}...{k[-4:]}"

def normalize_gemini_model(model: Optional[str]) -> str:
    m = (model or "").strip()
    if not m or m in ["gemini-2.0-flash", "models/gemini-2.0-flash", "gemini-2.5-flash", "models/gemini-2.5-flash"]:
        return "gemini-3.8-flash"
    if m.startswith("models/"):
        return m.replace("models/", "")
    return m

class AIAgentRouter:
    def __init__(self, gemini_api_key: str, deepseek_api_key: str, ha_bridge, data_dir: Optional[str] = None):
        self.ha_bridge = ha_bridge

        if data_dir:
            self.data_dir = data_dir
        else:
            candidates = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"),
                os.path.join(os.path.dirname(__file__), "data"),
                "/app/data"
            ]
            self.data_dir = next((c for c in candidates if os.path.exists(c)), candidates[0])

        os.makedirs(self.data_dir, exist_ok=True)
        self.config_file = os.path.join(self.data_dir, "ai_config.json")
        self.config = self._load_initial_config(gemini_api_key, deepseek_api_key)

    def _load_initial_config(self, default_gemini: str, default_deepseek: str) -> Dict[str, Any]:
        default_cfg = {
            "active_provider": "gemini",
            "gemini": {
                "api_key": default_gemini or os.getenv("GEMINI_API_KEY", ""),
                "model": "gemini-3.8-flash",
                "base_url": "https://generativelanguage.googleapis.com/v1beta"
            },
            "deepseek": {
                "api_key": default_deepseek or os.getenv("DEEPSEEK_API_KEY", ""),
                "model": "deepseek-flash",
                "base_url": "https://api.deepseek.com"
            },
            "openrouter": {
                "api_key": os.getenv("OPENROUTER_API_KEY", ""),
                "model": "google/gemini-2.0-flash-exp:free",
                "base_url": "https://openrouter.ai/api/v1"
            },
            "custom": {
                "api_key": "",
                "model": "",
                "base_url": "http://localhost:11434/v1"
            },
            "tts_voice": "vi-VN-HoaiMyNeural",
            "stt_service_url": os.getenv("STT_SERVICE_URL", "http://127.0.0.1:8095/v1/audio/transcriptions")
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    for k, v in saved.items():
                        if isinstance(v, dict) and k in default_cfg and isinstance(default_cfg[k], dict):
                            default_cfg[k].update(v)
                        else:
                            default_cfg[k] = v
                logger.info("Loaded AI Router config from %s", self.config_file)
            except Exception as e:
                logger.error("Failed to read %s: %s", self.config_file, e)

        # Normalize any saved gemini model
        default_cfg["gemini"]["model"] = normalize_gemini_model(default_cfg["gemini"].get("model"))
        return default_cfg

    def get_safe_config(self) -> Dict[str, Any]:
        """Trả về cấu hình an toàn cho Web UI (che giấu API keys)."""
        safe = {
            "active_provider": self.config.get("active_provider", "gemini"),
            "tts_voice": self.config.get("tts_voice", "vi-VN-HoaiMyNeural"),
            "stt_service_url": self.config.get("stt_service_url", "http://127.0.0.1:8095/v1/audio/transcriptions"),
            "gemini": {
                "api_key_masked": mask_key(self.config["gemini"].get("api_key")),
                "has_key": bool(self.config["gemini"].get("api_key")),
                "model": normalize_gemini_model(self.config["gemini"].get("model")),
                "base_url": self.config["gemini"].get("base_url", "https://generativelanguage.googleapis.com/v1beta")
            },
            "deepseek": {
                "api_key_masked": mask_key(self.config["deepseek"].get("api_key")),
                "has_key": bool(self.config["deepseek"].get("api_key")),
                "model": self.config["deepseek"].get("model", "deepseek-flash"),
                "base_url": self.config["deepseek"].get("base_url", "https://api.deepseek.com")
            },
            "openrouter": {
                "api_key_masked": mask_key(self.config["openrouter"].get("api_key")),
                "has_key": bool(self.config["openrouter"].get("api_key")),
                "model": self.config["openrouter"].get("model", "google/gemini-2.0-flash-exp:free"),
                "base_url": self.config["openrouter"].get("base_url", "https://openrouter.ai/api/v1")
            },
            "custom": {
                "api_key_masked": mask_key(self.config["custom"].get("api_key")),
                "has_key": bool(self.config["custom"].get("api_key")),
                "model": self.config["custom"].get("model", ""),
                "base_url": self.config["custom"].get("base_url", "")
            }
        }
        return safe

    def save_config(self, new_data: Dict[str, Any]) -> bool:
        """Lưu cấu hình mới, bảo toàn key cũ nếu người dùng không thay đổi."""
        try:
            if "active_provider" in new_data:
                self.config["active_provider"] = new_data["active_provider"]
            if "tts_voice" in new_data:
                self.config["tts_voice"] = new_data["tts_voice"]
            if "stt_service_url" in new_data:
                self.config["stt_service_url"] = new_data["stt_service_url"]

            for prov in ["gemini", "deepseek", "openrouter", "custom"]:
                if prov in new_data and isinstance(new_data[prov], dict):
                    p_data = new_data[prov]
                    if prov not in self.config:
                        self.config[prov] = {}

                    if "model" in p_data and p_data["model"]:
                        mod_val = p_data["model"].strip()
                        if prov == "gemini":
                            mod_val = normalize_gemini_model(mod_val)
                        self.config[prov]["model"] = mod_val

                    if "base_url" in p_data and p_data["base_url"]:
                        self.config[prov]["base_url"] = p_data["base_url"].strip()

                    new_key = p_data.get("api_key", "").strip()
                    if new_key and "..." not in new_key and "****" not in new_key:
                        self.config[prov]["api_key"] = new_key

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            logger.info("Saved AI configuration successfully to %s", self.config_file)
            return True
        except Exception as e:
            logger.error("Failed to save AI config: %s", e)
            return False

    def _get_ha_tools_schema_openai(self) -> List[Dict[str, Any]]:
        """Khai báo function calling tools theo chuẩn OpenAI (cho DeepSeek, OpenRouter)."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "control_home_device",
                    "description": "Bật, tắt thiết bị hoặc điều chỉnh nhiệt độ máy lạnh trong nhà.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_id": {
                                "type": "string",
                                "description": "ID chính xác của thiết bị trong Home Assistant (ví dụ: light.den_phong_khach, climate.may_lanh_phong_ngu, fan.quat_tran)."
                            },
                            "action": {
                                "type": "string",
                                "enum": ["turn_on", "turn_off", "toggle", "set_temperature"],
                                "description": "Hành động cần thực hiện trên thiết bị."
                            },
                            "temperature": {
                                "type": "number",
                                "description": "Nhiệt độ cài đặt nếu điều khiển máy lạnh (ví dụ: 25.0)."
                            }
                        },
                        "required": ["entity_id", "action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "master_turn_off_all",
                    "description": "Tắt toàn bộ thiết bị đang bật trong nhà (đèn, quạt, máy lạnh) khi người dùng ra khỏi nhà hoặc yêu cầu tắt hết.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "confirm": {
                                "type": "boolean",
                                "description": "Xác nhận tắt toàn bộ"
                            }
                        },
                        "required": ["confirm"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "activate_scene",
                    "description": "Kích hoạt kịch bản / ngữ cảnh (Scene) trong nhà.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scene_id": {
                                "type": "string",
                                "description": "ID ngữ cảnh (ví dụ: scene.tiep_khach, scene.di_ngu)."
                            }
                        },
                        "required": ["scene_id"]
                    }
                }
            }
        ]

    def _get_ha_tools_schema_gemini(self) -> List[Dict[str, Any]]:
        """Khai báo function declarations theo chuẩn Google Gemini REST."""
        return [
            {
                "name": "control_home_device",
                "description": "Bật, tắt thiết bị hoặc điều chỉnh nhiệt độ máy lạnh trong nhà.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "entity_id": {
                            "type": "STRING",
                            "description": "ID thiết bị trong Home Assistant (ví dụ: light.den_phong_khach)."
                        },
                        "action": {
                            "type": "STRING",
                            "enum": ["turn_on", "turn_off", "toggle", "set_temperature"],
                            "description": "Hành động điều khiển thiết bị."
                        },
                        "temperature": {
                            "type": "NUMBER",
                            "description": "Nhiệt độ cài đặt nếu là máy lạnh."
                        }
                    },
                    "required": ["entity_id", "action"]
                }
            },
            {
                "name": "master_turn_off_all",
                "description": "Tắt toàn bộ thiết bị đang bật trong nhà khi đi vắng hoặc đi ngủ.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "confirm": {
                            "type": "BOOLEAN",
                            "description": "Xác nhận tắt hết"
                        }
                    },
                    "required": ["confirm"]
                }
            },
            {
                "name": "activate_scene",
                "description": "Kích hoạt kịch bản ngữ cảnh trong nhà.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "scene_id": {
                            "type": "STRING",
                            "description": "ID ngữ cảnh (scene.tiep_khach, scene.di_ngu...)"
                        }
                    },
                    "required": ["scene_id"]
                }
            }
        ]

    def _build_device_context(self) -> str:
        """Tóm tắt danh sách thiết bị có trong Home Assistant để đưa vào context của AI."""
        if not self.ha_bridge:
            return "Không có kết nối tới Home Assistant."

        entities = self.ha_bridge.get_entities_list()
        if not entities:
            return "Chưa tải được danh sách thiết bị từ Home Assistant."

        lines = []
        for e in entities:
            domain = e.get("domain", "")
            if domain in ["light", "switch", "climate", "fan", "cover", "scene"]:
                eid = e.get("entity_id", "")
                name = e.get("name", eid)
                area = e.get("area_name", "Chung")
                state = e.get("state", "off")
                lines.append(f"- {name} ({eid}) | Phòng: {area} | Trạng thái: {state}")

        return "\n".join(lines[:50])

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Thực thi action gọi thiết bị vào Home Assistant."""
        logger.info("Executing HA Tool: %s with args %s", name, args)
        try:
            if name == "control_home_device":
                eid = args.get("entity_id", "")
                action = args.get("action", "turn_on")
                domain = eid.split(".")[0] if "." in eid else "light"

                if action == "set_temperature":
                    temp = args.get("temperature", 25)
                    await self.ha_bridge.call_service("climate", "set_temperature", eid, {"temperature": float(temp)})
                    return f"Đã chỉnh nhiệt độ {eid} thành {temp}°C."
                elif action == "turn_on":
                    await self.ha_bridge.call_service(domain, "turn_on", eid)
                    return f"Đã bật {eid} thành công."
                elif action == "turn_off":
                    await self.ha_bridge.call_service(domain, "turn_off", eid)
                    return f"Đã tắt {eid} thành công."
                elif action == "toggle":
                    await self.ha_bridge.call_service(domain, "toggle", eid)
                    return f"Đã đổi trạng thái {eid}."

            elif name == "master_turn_off_all":
                res = await self.ha_bridge.master_turn_off_all()
                count = res.get("turned_off_count", 0)
                return f"Đã tắt toàn bộ {count} thiết bị trong nhà."

            elif name == "activate_scene":
                sid = args.get("scene_id", "")
                await self.ha_bridge.call_service("scene", "turn_on", sid)
                return f"Đã kích hoạt ngữ cảnh {sid}."

        except Exception as e:
            logger.error("Error executing tool %s: %s", name, e)
            return f"Lỗi khi điều khiển thiết bị: {str(e)}"

        return "Không nhận diện được công cụ phù hợp."

    async def test_connection(self, provider: str, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
        """Test latency và kết nối đến AI provider theo chuẩn chính thức của từng hãng."""
        t0 = time.time()
        prov_cfg = self.config.get(provider, {})
        key = api_key or prov_cfg.get("api_key", "")
        mod = model or prov_cfg.get("model", "")
        url = base_url or prov_cfg.get("base_url", "")

        if not key:
            return {"status": "error", "message": f"Chưa có API Key cho {provider}"}

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                # 1. GOOGLE GEMINI (Interactions API / generateContent)
                if provider == "gemini":
                    norm_mod = normalize_gemini_model(mod)
                    endpoint = "https://generativelanguage.googleapis.com/v1beta/interactions"
                    headers = {
                        "x-goog-api-key": key,
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": norm_mod,
                        "input": "Trả lời 'OK' nếu bạn nhận được tin này."
                    }
                    res = await client.post(endpoint, headers=headers, json=payload)
                    elapsed = int((time.time() - t0) * 1000)
                    if res.status_code == 200:
                        data = res.json()
                        reply = data.get("output_text") or data.get("text") or "OK"
                        return {"status": "success", "latency_ms": elapsed, "reply": reply.strip(), "model": norm_mod, "provider": provider}
                    elif res.status_code == 503:
                        return {"status": "warning", "http_code": 503, "message": f"Máy chủ Google báo model {norm_mod} đang chịu tải cao tạm thời (High Demand). API key và kết nối hoàn toàn hợp lệ!", "latency_ms": elapsed}
                    else:
                        # Fallback thử endpoint generateContent
                        fb_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{norm_mod}:generateContent"
                        fb_payload = {
                            "contents": [{"parts": [{"text": "Trả lời 'OK'"}]}],
                            "generationConfig": {"maxOutputTokens": 10, "temperature": 0.2}
                        }
                        res_fb = await client.post(fb_endpoint, headers=headers, json=fb_payload)
                        if res_fb.status_code == 200:
                            data = res_fb.json()
                            reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                            return {"status": "success", "latency_ms": int((time.time() - t0) * 1000), "reply": reply, "model": norm_mod, "provider": provider}
                        elif res_fb.status_code == 503:
                            return {"status": "warning", "http_code": 503, "message": f"Máy chủ Google báo model {norm_mod} đang chịu tải cao (High Demand). API key đã xác thực thành công!", "latency_ms": int((time.time() - t0) * 1000)}
                        return {"status": "error", "http_code": res.status_code, "message": res.text[:250], "latency_ms": elapsed}

                # 2. DEEPSEEK OFFICIAL API (api.deepseek.com/chat/completions)
                elif provider == "deepseek":
                    norm_mod = mod or "deepseek-flash"
                    endpoint = "https://api.deepseek.com/chat/completions"
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
                        return {"status": "error", "http_code": 401, "message": "API Key DeepSeek không hợp lệ hoặc đã hết hạn (Authentication Fails). Vui lòng kiểm tra lại trên platform.deepseek.com/api_keys", "latency_ms": elapsed}
                    else:
                        return {"status": "error", "http_code": res.status_code, "message": res.text[:250], "latency_ms": elapsed}

                # 3. OPENROUTER (9 Router) API (openrouter.ai/api/v1/chat/completions)
                elif provider == "openrouter":
                    norm_mod = mod or "google/gemini-2.0-flash-exp:free"
                    endpoint = "https://openrouter.ai/api/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://nalasmarthome.local",
                        "X-Title": "NALA Smart Home Hub"
                    }
                    payload = {
                        "model": norm_mod,
                        "messages": [
                            {"role": "user", "content": "Trả lời 'OK' nếu bạn nhận được tin này."}
                        ],
                        "max_tokens": 10
                    }
                    res = await client.post(endpoint, headers=headers, json=payload)
                    elapsed = int((time.time() - t0) * 1000)
                    if res.status_code == 200:
                        data = res.json()
                        reply = data["choices"][0]["message"]["content"].strip()
                        return {"status": "success", "latency_ms": elapsed, "reply": reply, "model": norm_mod, "provider": provider}
                    else:
                        return {"status": "error", "http_code": res.status_code, "message": res.text[:250], "latency_ms": elapsed}

                # 4. CUSTOM OPENAI-COMPATIBLE
                else:
                    endpoint = f"{url.rstrip('/')}/chat/completions"
                    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                    payload = {
                        "model": mod,
                        "messages": [{"role": "user", "content": "Trả lời 'OK'"}],
                        "max_tokens": 10
                    }
                    res = await client.post(endpoint, headers=headers, json=payload)
                    elapsed = int((time.time() - t0) * 1000)
                    if res.status_code == 200:
                        data = res.json()
                        reply = data["choices"][0]["message"]["content"].strip()
                        return {"status": "success", "latency_ms": elapsed, "reply": reply, "model": mod, "provider": provider}
                    else:
                        return {"status": "error", "http_code": res.status_code, "message": res.text[:250], "latency_ms": elapsed}

        except Exception as e:
            elapsed = int((time.time() - t0) * 1000)
            err_msg = str(e)
            if isinstance(e, httpx.TimeoutException):
                err_msg = f"Hết thời gian chờ phản hồi từ {provider} ({elapsed}ms). Máy chủ có thể đang chịu tải cao hoặc đường truyền chậm."
            return {"status": "error", "message": err_msg, "latency_ms": elapsed}

    async def process_intent(self, user_text: str, context_room: str = "", model_preference: Optional[str] = None) -> str:
        """Xử lý giọng nói người dùng, kết hợp Fast-Rule và Multi-AI Function Calling."""
        if not user_text:
            return "Tôi không nghe thấy gì cả."

        lower_text = user_text.lower().strip()

        # 1. FAST-PATH RULE BASED (<20ms) cho các lệnh thường gặp
        if any(w in lower_text for w in ["tắt hết", "tắt toàn bộ", "tắt cả nhà", "đi ngủ", "ra khỏi nhà"]):
            res = await self.ha_bridge.master_turn_off_all()
            cnt = res.get("turned_off_count", 0)
            return f"Đã tắt {cnt} thiết bị trong nhà cho bạn."

        # 2. Xác định AI Provider
        prov = model_preference or self.config.get("active_provider", "gemini")
        if prov not in self.config or not self.config[prov].get("api_key"):
            for alt in ["gemini", "deepseek", "openrouter", "custom"]:
                if self.config.get(alt, {}).get("api_key"):
                    prov = alt
                    break

        prov_cfg = self.config.get(prov, {})
        api_key = prov_cfg.get("api_key", "")
        model = prov_cfg.get("model", "")
        base_url = prov_cfg.get("base_url", "")

        if not api_key:
            return f"Tôi đã nghe: '{user_text}', nhưng hệ thống chưa được cài đặt API Key AI."

        device_ctx = self._build_device_context()
        system_instruction = SYSTEM_PROMPT_TEMPLATE.format(
            device_context=device_ctx,
            current_room=context_room or "Không xác định"
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # -------------------------------------------------------------
                # GOOGLE GEMINI NATIVE REST (generateContent)
                # -------------------------------------------------------------
                if prov == "gemini":
                    norm_mod = normalize_gemini_model(model)
                    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{norm_mod}:generateContent"
                    headers = {
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "system_instruction": {
                            "parts": [{"text": system_instruction}]
                        },
                        "contents": [
                            {"role": "user", "parts": [{"text": user_text}]}
                        ],
                        "tools": [
                            {"function_declarations": self._get_ha_tools_schema_gemini()}
                        ],
                        "generationConfig": {
                            "temperature": 0.4,
                            "maxOutputTokens": 150
                        }
                    }
                    res = await client.post(endpoint, headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        candidate = data.get("candidates", [{}])[0]
                        parts = candidate.get("content", {}).get("parts", [])

                        # Kiểm tra function call
                        confirmations = []
                        text_replies = []
                        for part in parts:
                            if "functionCall" in part:
                                fn = part["functionCall"]
                                fn_name = fn.get("name", "")
                                fn_args = fn.get("args", {})
                                res_msg = await self.execute_tool(fn_name, fn_args)
                                confirmations.append(res_msg)
                            elif "text" in part:
                                text_replies.append(part["text"].strip())

                        if confirmations:
                            return " ".join(confirmations)
                        if text_replies:
                            return " ".join(text_replies)
                    else:
                        logger.error("Gemini API error %d: %s", res.status_code, res.text)
                        return f"Xin lỗi, Gemini báo lỗi ({res.status_code})."

                # -------------------------------------------------------------
                # DEEPSEEK & OPENROUTER (OpenAI Chat Completions Format)
                # -------------------------------------------------------------
                else:
                    if prov == "deepseek":
                        endpoint = "https://api.deepseek.com/chat/completions"
                        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                        use_model = model or "deepseek-chat"
                    elif prov == "openrouter":
                        endpoint = "https://openrouter.ai/api/v1/chat/completions"
                        headers = {
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://nalasmarthome.local",
                            "X-Title": "NALA Smart Home Hub"
                        }
                        use_model = model or "google/gemini-2.0-flash-exp:free"
                    else:
                        endpoint = f"{base_url.rstrip('/')}/chat/completions"
                        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                        use_model = model

                    payload = {
                        "model": use_model,
                        "messages": [
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": user_text}
                        ],
                        "tools": self._get_ha_tools_schema_openai(),
                        "tool_choice": "auto",
                        "max_tokens": 150,
                        "temperature": 0.4
                    }

                    res = await client.post(endpoint, headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        msg = data["choices"][0]["message"]
                        tool_calls = msg.get("tool_calls", [])
                        if tool_calls:
                            confirmations = []
                            for tc in tool_calls:
                                func = tc.get("function", {})
                                fn_name = func.get("name", "")
                                raw_args = func.get("arguments", "{}")
                                try:
                                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                                except Exception:
                                    args = {}
                                res_msg = await self.execute_tool(fn_name, args)
                                confirmations.append(res_msg)
                            if confirmations:
                                return " ".join(confirmations)
                            return "Đã thực hiện yêu cầu cho bạn."

                        content = msg.get("content", "").strip()
                        if content:
                            return content
                    else:
                        logger.error("AI Provider %s error %d: %s", prov, res.status_code, res.text)
                        return f"Xin lỗi, {prov} báo lỗi ({res.status_code})."

        except Exception as e:
            logger.error("Error communicating with AI Provider %s: %s", prov, e)

        return "Xin lỗi, hiện tại tôi gặp sự cố khi kết nối tới trợ lý AI."
