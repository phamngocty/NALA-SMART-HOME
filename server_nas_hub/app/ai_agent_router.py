"""
NALA SMART HOME - ADVANCED AI AGENT ROUTER
Implements official specs:
- Google Gemini: Native Generative Language API (generateContent) with x-goog-api-key & Function Declarations
- DeepSeek: Official OpenAI-compatible Chat Completions API (api.deepseek.com)
- OpenRouter (9 Router): Official OpenRouter API (openrouter.ai/api/v1)
Includes Home Assistant Tool Calling & Room-Context Awareness.
"""

import os
import re
import json
import time
import asyncio
import logging
import unicodedata
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx

logger = logging.getLogger("AIRouter")

SYSTEM_PROMPT_TEMPLATE = """Bạn là Nala - Trợ lý giọng nói và quản gia AI của hệ thống NALA Smart Home.
Nhiệm vụ của bạn:
1. Trả lời cực kỳ ngắn gọn, tự nhiên, thân thiện bằng tiếng Việt (tối đa 1-2 câu) để đọc qua loa không bị rườm rà.
2. Điều khiển thiết bị nhà thông minh bằng cách gọi các công cụ (tools) phù hợp khi người dùng yêu cầu bật/tắt thiết bị, điều chỉnh nhiệt độ máy lạnh, tắt hết toàn nhà,...
3. NGỮ CẢNH VỊ TRÍ: Người dùng đang đứng tại phòng: [{current_room}]. Nếu người dùng ra lệnh điều khiển chung chung như 'bật đèn', 'tắt quạt', 'máy lạnh 24 độ' mà không nhắc tên phòng khác, BẮT BUỘC ưu tiên chọn thiết bị thuộc phòng [{current_room}].
4. QUY TẮC CHỌN ENTITY ID: BẮT BUỘC chỉ sử dụng chính xác mã `entity_id` nằm trong dấu ngoặc tròn `(...)` ở danh sách thiết bị bên dưới (Ví dụ: `climate.150633094640317_climate`, `light.cong_tat_phong_khach_tret_den_1`). TUYỆT ĐỐI KHÔNG tự bịa hoặc tự dịch tên tiếng Việt thành entity_id giả!
5. Nếu người dùng hỏi thông tin bình thường (thời tiết, kiến thức, chào hỏi...), hãy trả lời hóm hỉnh và súc tích.

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
    if not m or m in ["gemini-2.0-flash", "models/gemini-2.0-flash", "gemini-2.5-flash", "models/gemini-2.5-flash", "gemini-3.8-flash", "models/gemini-3.8-flash", "gemini-flash-latest", "models/gemini-flash-latest"]:
        return "gemini-flash-lite-latest"
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
                "model": "gemini-flash-lite-latest",
                "base_url": "https://generativelanguage.googleapis.com/v1beta"
            },
            "deepseek": {
                "api_key": default_deepseek or os.getenv("DEEPSEEK_API_KEY", ""),
                "model": "deepseek-flash",
                "base_url": "https://api.deepseek.com"
            },
            "groq": {
                "api_key": os.getenv("GROQ_API_KEY", ""),
                "model": "llama-3.3-70b-versatile",
                "base_url": "https://api.groq.com/openai/v1"
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
            "stt_service_url": os.getenv("STT_SERVICE_URL", "http://127.0.0.1:8095/v1/audio/transcriptions"),
            "stt_provider": "auto",
            "stt_groq_model": "whisper-large-v3-turbo",
            "auto_fallback": True
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
            "stt_provider": self.config.get("stt_provider", "auto"),
            "stt_groq_model": self.config.get("stt_groq_model", "whisper-large-v3-turbo"),
            "auto_fallback": self.config.get("auto_fallback", True),
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
            "groq": {
                "api_key_masked": mask_key(self.config.get("groq", {}).get("api_key")),
                "has_key": bool(self.config.get("groq", {}).get("api_key")),
                "model": self.config.get("groq", {}).get("model", "llama-3.3-70b-versatile"),
                "base_url": self.config.get("groq", {}).get("base_url", "https://api.groq.com/openai/v1")
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
            if "stt_provider" in new_data:
                self.config["stt_provider"] = new_data["stt_provider"]
            if "stt_groq_model" in new_data:
                self.config["stt_groq_model"] = new_data["stt_groq_model"]
            if "auto_fallback" in new_data:
                self.config["auto_fallback"] = bool(new_data["auto_fallback"])

            for prov in ["gemini", "deepseek", "groq", "openrouter", "custom"]:
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

        priority_domains = ["climate", "fan", "scene", "cover", "switch", "light"]

        def sort_key(e):
            dom = e.get("domain") or e.get("entity_id", "").split(".")[0]
            try:
                return priority_domains.index(dom)
            except ValueError:
                return 99

        sorted_entities = sorted(entities, key=sort_key)
        lines = []
        for e in sorted_entities:
            dom = e.get("domain") or e.get("entity_id", "").split(".")[0]
            if dom in priority_domains:
                eid = e.get("entity_id", "")
                name = e.get("name") or e.get("attributes", {}).get("friendly_name") or eid
                area = e.get("area_name", "Chung")
                state = e.get("state", "off")
                lines.append(f"- {name} ({eid}) | Phòng: {area} | Trạng thái: {state}")

        # Tăng giới hạn lên 120 để bao phủ toàn bộ thiết bị trong nhà, đảm bảo máy lạnh không bị cắt xén
        return "\n".join(lines[:120])

    def _resolve_real_entity_id(self, raw_eid: str, target_domain: str = "") -> tuple:
        """Tự động phân giải entity_id thật nếu LLM gọi nhầm mã ảo hoặc tên không dấu."""
        if not self.ha_bridge:
            return raw_eid, raw_eid

        entities = self.ha_bridge.get_entities_list()
        # 1. Khớp chính xác 100%
        for e in entities:
            if e.get("entity_id") == raw_eid:
                fname = e.get("name") or e.get("attributes", {}).get("friendly_name") or raw_eid
                return raw_eid, fname

        # 2. Fuzzy match theo từ khóa
        def remove_accents(s):
            if not s:
                return ""
            s1 = unicodedata.normalize('NFD', s)
            s2 = "".join(c for c in s1 if unicodedata.category(c) != 'Mn')
            return s2.replace('đ', 'd').replace('Đ', 'D').lower()

        clean_query = remove_accents(raw_eid.replace(".", " ").replace("_", " "))
        tokens = [t for t in re.split(r'\s+', clean_query) if len(t) > 1 and t not in ["climate", "light", "switch", "fan", "cover", "scene"]]

        best_match = None
        best_score = 0

        for e in entities:
            dom = e.get("domain") or e.get("entity_id", "").split(".")[0]
            if target_domain and dom != target_domain:
                continue

            name = e.get("name") or e.get("attributes", {}).get("friendly_name") or ""
            area = e.get("area_name") or ""
            target_str = remove_accents(f"{e.get('entity_id')} {name} {area}")

            score = sum(1 for t in tokens if t in target_str)
            if score > best_score:
                best_score = score
                best_match = e

        if best_match and best_score >= 1:
            fname = best_match.get("attributes", {}).get("friendly_name") or best_match.get("name") or best_match.get("entity_id")
            logger.info("Fuzzy resolved entity [%s] -> Real [%s] (%s)", raw_eid, best_match.get("entity_id"), fname)
            return best_match.get("entity_id"), fname

        return raw_eid, raw_eid

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Thực thi action gọi thiết bị vào Home Assistant."""
        logger.info("Executing HA Tool: %s with args %s", name, args)
        try:
            if name == "control_home_device":
                raw_eid = args.get("entity_id", "")
                action = args.get("action", "turn_on")
                domain = "climate" if action == "set_temperature" else (raw_eid.split(".")[0] if "." in raw_eid else "light")

                eid, friendly_name = self._resolve_real_entity_id(raw_eid, domain)

                if action == "set_temperature":
                    temp = args.get("temperature", 25)
                    await self.ha_bridge.call_service("climate", "set_temperature", eid, {"temperature": float(temp)})
                    return f"Đã chỉnh nhiệt độ {friendly_name} thành {temp}°C."
                elif action == "turn_on":
                    await self.ha_bridge.call_service(domain, "turn_on", eid)
                    return f"Đã bật {friendly_name} thành công."
                elif action == "turn_off":
                    await self.ha_bridge.call_service(domain, "turn_off", eid)
                    return f"Đã tắt {friendly_name} thành công."
                elif action == "toggle":
                    await self.ha_bridge.call_service(domain, "toggle", eid)
                    return f"Đã đổi trạng thái {friendly_name}."

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
        raw_key = (api_key or "").strip()
        if not raw_key or "..." in raw_key or "****" in raw_key:
            key = prov_cfg.get("api_key", "")
        else:
            key = raw_key

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
                        err_msg = res_fb.text if res_fb.text else res.text
                        if "Rate limit exceeded" in err_msg or "too_many_requests" in err_msg or res_fb.status_code == 429:
                            return {
                                "status": "error",
                                "http_code": 429,
                                "message": f"Google Free Tier giới hạn model {norm_mod} (Google tự động trỏ '{norm_mod}' vào model bị giới hạn 20 req/ngày). Vui lòng chọn 'gemini-flash-lite-latest' hoặc 'gemini-3.5-flash' để dùng miễn phí không lo giới hạn!",
                                "latency_ms": int((time.time() - t0) * 1000)
                            }
                        return {"status": "error", "http_code": res_fb.status_code or res.status_code, "message": err_msg[:250], "latency_ms": elapsed}

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
                        "thinking": {"type": "disabled"},
                        "max_tokens": 100,
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

                # 3. GROQ CLOUD OFFICIAL API (api.groq.com/openai/v1/chat/completions)
                elif provider == "groq":
                    norm_mod = mod or "llama-3.3-70b-versatile"
                    endpoint = "https://api.groq.com/openai/v1/chat/completions"
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
                        return {"status": "error", "http_code": 401, "message": "API Key Groq không hợp lệ (gsk_...). Vui lòng kiểm tra lại trên console.groq.com/keys", "latency_ms": elapsed}
                    else:
                        return {"status": "error", "http_code": res.status_code, "message": res.text[:250], "latency_ms": elapsed}

                # 4. OPENROUTER (9 Router) API (openrouter.ai/api/v1/chat/completions)
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

    async def list_available_models(self, provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> List[Dict[str, str]]:
        """Lấy danh sách các model khả dụng từ API chính thức của từng provider."""
        prov_cfg = self.config.get(provider, {})
        raw_key = (api_key or "").strip()
        if not raw_key or "..." in raw_key or "****" in raw_key:
            key = prov_cfg.get("api_key", "")
        else:
            key = raw_key

        url = base_url or prov_cfg.get("base_url", "")
        models: List[Dict[str, str]] = []

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                # 1. GOOGLE GEMINI
                if provider == "gemini":
                    if key:
                        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
                        res = await client.get(endpoint)
                        if res.status_code == 200:
                            data = res.json()
                            for m in data.get("models", []):
                                methods = m.get("supportedGenerationMethods", [])
                                if "generateContent" in methods:
                                    m_id = m.get("name", "").replace("models/", "")
                                    disp = m.get("displayName") or m_id
                                    models.append({"id": m_id, "name": f"{m_id} ({disp})"})

                    top_gemini = [
                        {"id": "gemini-flash-lite-latest", "name": "gemini-flash-lite-latest (Khuyên dùng - Miễn phí tốc độ cao)"},
                        {"id": "gemini-3.5-flash", "name": "gemini-3.5-flash (Bản 3.5 Flash ổn định)"},
                        {"id": "gemini-3.5-flash-lite", "name": "gemini-3.5-flash-lite (Bản 3.5 Lite nhẹ)"},
                        {"id": "gemini-flash-latest", "name": "gemini-flash-latest (Google trỏ 3.8 - Giới hạn 20 req/ngày)"},
                        {"id": "gemini-3.8-flash", "name": "gemini-3.8-flash (Bản 3.8 - Giới hạn 20 req/ngày)"},
                        {"id": "gemini-pro-latest", "name": "gemini-pro-latest (Bản Pro mới nhất)"}
                    ]
                    if not models:
                        return top_gemini
                    existing_ids = {m["id"] for m in models}
                    ordered = [m for m in top_gemini if m["id"] in existing_ids or not models]
                    for m in models:
                        if m["id"] not in {x["id"] for x in ordered}:
                            ordered.append(m)
                    return ordered

                # 2. GROQ CLOUD
                elif provider == "groq":
                    if key:
                        endpoint = "https://api.groq.com/openai/v1/models"
                        headers = {"Authorization": f"Bearer {key}"}
                        res = await client.get(endpoint, headers=headers)
                        if res.status_code == 200:
                            data = res.json()
                            for m in data.get("data", []):
                                m_id = m.get("id", "")
                                if "whisper" in m_id.lower() or "guard" in m_id.lower():
                                    continue
                                desc = ""
                                if "llama-3.3-70b" in m_id:
                                    desc = " (Khuyên dùng - 70B Đỉnh cao Siêu tốc)"
                                elif "llama-3.1-8b" in m_id:
                                    desc = " (8B Siêu nhẹ ~800 tokens/s)"
                                elif "mixtral" in m_id:
                                    desc = " (MoE 32k Context)"
                                elif "deepseek" in m_id:
                                    desc = " (DeepSeek R1 Distill)"
                                elif "qwen" in m_id:
                                    desc = " (Qwen 2.5)"
                                models.append({"id": m_id, "name": f"{m_id}{desc}"})

                    default_groq = [
                        {"id": "llama-3.3-70b-versatile", "name": "llama-3.3-70b-versatile (Khuyên dùng - 70B Đỉnh cao Siêu tốc)"},
                        {"id": "llama-3.1-8b-instant", "name": "llama-3.1-8b-instant (8B Siêu nhẹ ~800 tokens/s)"},
                        {"id": "llama-3.2-3b-preview", "name": "llama-3.2-3b-preview (3B Nhẹ gọn)"},
                        {"id": "llama-3.2-11b-vision-preview", "name": "llama-3.2-11b-vision-preview (11B Đa phương tiện)"},
                        {"id": "deepseek-r1-distill-llama-70b", "name": "deepseek-r1-distill-llama-70b (Suy luận R1)"},
                        {"id": "qwen-2.5-32b", "name": "qwen-2.5-32b (Qwen 32B Cân bằng)"},
                        {"id": "mixtral-8x7b-32768", "name": "mixtral-8x7b-32768 (MoE 32k Context)"},
                        {"id": "gemma2-9b-it", "name": "gemma2-9b-it (Google Gemma 2)"}
                    ]
                    if not models:
                        return default_groq
                    existing = {m["id"] for m in models}
                    ordered = [m for m in default_groq if m["id"] in existing]
                    for m in models:
                        if m["id"] not in {x["id"] for x in ordered}:
                            ordered.append(m)
                    return ordered

                # 3. DEEPSEEK
                elif provider == "deepseek":
                    if key:
                        endpoint = "https://api.deepseek.com/models"
                        headers = {"Authorization": f"Bearer {key}"}
                        res = await client.get(endpoint, headers=headers)
                        if res.status_code == 200:
                            data = res.json()
                            for m in data.get("data", []):
                                m_id = m.get("id", "")
                                models.append({"id": m_id, "name": m_id})
                    if not models:
                        return [
                            {"id": "deepseek-flash", "name": "deepseek-flash (Khuyên dùng - V4 Flash)"},
                            {"id": "deepseek-chat", "name": "deepseek-chat (V3 Cân bằng)"},
                            {"id": "deepseek-reasoner", "name": "deepseek-reasoner (R1 Suy luận sâu)"}
                        ]
                    return models

                # 4. OPENROUTER
                elif provider == "openrouter":
                    endpoint = "https://openrouter.ai/api/v1/models"
                    headers = {"Authorization": f"Bearer {key}"} if key else {}
                    res = await client.get(endpoint, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        raw_list = data.get("data", [])
                        free_models = []
                        top_models = []
                        for m in raw_list:
                            m_id = m.get("id", "")
                            m_name = m.get("name", m_id)
                            if ":free" in m_id:
                                free_models.append({"id": m_id, "name": f"{m_id} [Miễn phí]"})
                            elif any(k in m_id for k in ["gemini-2.0-flash", "llama-3.3-70b", "deepseek/deepseek-chat", "claude-3.5-haiku"]):
                                top_models.append({"id": m_id, "name": f"{m_id} ({m_name})"})
                        return free_models + top_models
                    return [
                        {"id": "google/gemini-2.0-flash-exp:free", "name": "google/gemini-2.0-flash-exp:free [Miễn phí]"},
                        {"id": "deepseek/deepseek-chat", "name": "deepseek/deepseek-chat (DeepSeek V3)"},
                        {"id": "meta-llama/llama-3.3-70b-instruct", "name": "meta-llama/llama-3.3-70b-instruct"}
                    ]

                # 5. CUSTOM / OLLAMA / LOCAL
                else:
                    if url:
                        base = url.rstrip('/')
                        if not base.endswith('/v1'):
                            base += '/v1'
                        endpoint = f"{base}/models"
                        headers = {"Authorization": f"Bearer {key}"} if key else {}
                        res = await client.get(endpoint, headers=headers)
                        if res.status_code == 200:
                            data = res.json()
                            for m in data.get("data", []):
                                m_id = m.get("id", "")
                                models.append({"id": m_id, "name": m_id})
                    return models or [{"id": "qwen2.5:3b", "name": "qwen2.5:3b (Ollama Default)"}]

        except Exception as e:
            logger.error("Error fetching models for %s: %s", provider, e)
            return []



    async def _try_local_rule_fallback(self, user_text: str, context_room: str = "") -> Optional[str]:
        """Dự phòng offline nội bộ qua Home Assistant khi toàn bộ Cloud AI bị đứt mạng hoặc quá tải."""
        if not user_text or not self.ha_bridge:
            return None
        t = user_text.lower().strip()

        is_turn_on = any(w in t for w in ["bật", "mở", "khởi động", "set", "chỉnh"])
        is_turn_off = any(w in t for w in ["tắt", "đóng", "ngắt", "dừng"])
        if not is_turn_on and not is_turn_off:
            return None

        action = "turn_on" if is_turn_on else "turn_off"
        action_name = "bật" if is_turn_on else "tắt"

        target_domain = ""
        if any(w in t for w in ["máy lạnh", "điều hòa", "ac"]):
            target_domain = "climate"
        elif any(w in t for w in ["đèn", "ánh sáng", "led"]):
            target_domain = "light"
        elif any(w in t for w in ["quạt", "fan"]):
            target_domain = "fan"
        elif any(w in t for w in ["công tắc", "ổ cắm"]):
            target_domain = "switch"

        matched_eid = None
        matched_name = None
        room_lower = (context_room or "").lower()

        for eid, state_obj in self.ha_bridge.states.items():
            domain = eid.split(".")[0]
            if target_domain and domain != target_domain:
                continue
            attrs = state_obj.get("attributes", {})
            friendly_name = attrs.get("friendly_name", "").lower()

            if room_lower and room_lower in t:
                if room_lower in friendly_name or room_lower in eid.lower():
                    matched_eid = eid
                    matched_name = attrs.get("friendly_name", eid)
                    break
            elif target_domain:
                if room_lower and (room_lower in friendly_name or room_lower in eid.lower()):
                    matched_eid = eid
                    matched_name = attrs.get("friendly_name", eid)
                    break
                elif not matched_eid:
                    matched_eid = eid
                    matched_name = attrs.get("friendly_name", eid)

        if matched_eid:
            domain = matched_eid.split(".")[0]
            try:
                if domain == "climate":
                    if is_turn_off:
                        await self.ha_bridge.call_service("climate", "set_hvac_mode", entity_id=matched_eid, service_data={"hvac_mode": "off"})
                    else:
                        await self.ha_bridge.call_service("climate", "set_hvac_mode", entity_id=matched_eid, service_data={"hvac_mode": "cool"})
                else:
                    await self.ha_bridge.call_service(domain, action, entity_id=matched_eid)
                return f"Đã {action_name} {matched_name or matched_eid} theo lệnh dự phòng nội bộ."
            except Exception as ex:
                logger.error("Local rule execution error for %s: %s", matched_eid, ex)

        return None

    async def process_intent(self, user_text: str, context_room: str = "", model_preference: Optional[str] = None) -> str:
        """Xử lý giọng nói người dùng, kết hợp Fast-Rule, Multi-AI Function Calling và Cơ chế Tự Động Dự Phòng (Failover/Fallback)."""
        if not user_text:
            return "Tôi không nghe thấy gì cả."

        lower_text = user_text.lower().strip()

        # 1. FAST-PATH RULE BASED (<20ms) cho các lệnh thường gặp
        if any(w in lower_text for w in ["tắt hết", "tắt toàn bộ", "tắt cả nhà", "đi ngủ", "ra khỏi nhà"]):
            res = await self.ha_bridge.master_turn_off_all()
            cnt = res.get("turned_off_count", 0)
            return f"Đã tắt {cnt} thiết bị trong nhà cho bạn."

        # 2. Xây dựng danh sách ứng viên Provider theo thứ tự ưu tiên (Primary -> Fallbacks)
        preferred = model_preference or self.config.get("active_provider", "gemini")
        auto_fallback = self.config.get("auto_fallback", True)

        candidates = []
        if self.config.get(preferred, {}).get("api_key"):
            candidates.append(preferred)

        if auto_fallback:
            for alt in ["groq", "deepseek", "gemini", "openrouter", "custom"]:
                if alt != preferred and self.config.get(alt, {}).get("api_key"):
                    candidates.append(alt)

        if not candidates:
            local_res = await self._try_local_rule_fallback(user_text, context_room)
            if local_res:
                return local_res
            return f"Tôi đã nghe: '{user_text}', nhưng hệ thống chưa được cài đặt API Key AI khả dụng."

        device_ctx = self._build_device_context()
        system_instruction = SYSTEM_PROMPT_TEMPLATE.format(
            device_context=device_ctx,
            current_room=context_room or "Không xác định"
        )

        last_error_desc = ""

        for prov_idx, prov in enumerate(candidates):
            prov_cfg = self.config.get(prov, {})
            api_key = prov_cfg.get("api_key", "")
            model = prov_cfg.get("model", "")
            base_url = prov_cfg.get("base_url", "")

            logger.info("Processing intent with [%s] (Candidate %d/%d, model: %s)...",
                        prov, prov_idx + 1, len(candidates), model)

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    if prov == "gemini":
                        norm_mod = normalize_gemini_model(model)
                        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{norm_mod}:generateContent"
                        headers = {
                            "x-goog-api-key": api_key,
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "system_instruction": {"parts": [{"text": system_instruction}]},
                            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
                            "tools": [{"function_declarations": self._get_ha_tools_schema_gemini()}],
                            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 150}
                        }
                        res = await client.post(endpoint, headers=headers, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            candidate = data.get("candidates", [{}])[0]
                            parts = candidate.get("content", {}).get("parts", [])

                            confirmations = []
                            text_replies = []
                            for part in parts:
                                if "functionCall" in part:
                                    fn = part["functionCall"]
                                    res_msg = await self.execute_tool(fn.get("name", ""), fn.get("args", {}))
                                    confirmations.append(res_msg)
                                elif "text" in part:
                                    text_replies.append(part["text"].strip())

                            if confirmations:
                                return " ".join(confirmations)
                            if text_replies:
                                return " ".join(text_replies)
                        else:
                            last_error_desc = f"Gemini HTTP {res.status_code}"
                            logger.warning("Gemini API error %d: %s. Auto-falling back to next provider...",
                                           res.status_code, res.text[:120])
                            continue

                    else:
                        if prov == "groq":
                            endpoint = "https://api.groq.com/openai/v1/chat/completions"
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                            use_model = model or "llama-3.3-70b-versatile"
                        elif prov == "deepseek":
                            endpoint = "https://api.deepseek.com/chat/completions"
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                            use_model = model or "deepseek-flash"
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
                        if prov == "deepseek":
                            payload["thinking"] = {"type": "disabled"}

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
                            last_error_desc = f"{prov} HTTP {res.status_code}"
                            logger.warning("Provider '%s' error %d: %s. Auto-falling back...",
                                           prov, res.status_code, res.text[:120])
                            continue

            except Exception as e:
                last_error_desc = str(e)
                logger.warning("Exception communicating with AI Provider '%s': %s. Auto-falling back...", prov, e)
                continue

        logger.error("All AI providers failed (%s). Triggering offline local rule fallback...", last_error_desc)
        local_res = await self._try_local_rule_fallback(user_text, context_room)
        if local_res:
            return local_res

        return f"Xin lỗi, các máy chủ AI đều đang bận ({last_error_desc}). Vui lòng thử lại sau ít giây."

    async def stream_intent(self, user_text: str, context_room: str = "", model_preference: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream kết quả đối thoại thời gian thực từng token với cơ chế Tự Động Dự Phòng (Failover / Fallback)."""
        if not user_text or not user_text.strip():
            yield "Tôi không nghe thấy gì cả."
            return

        lower_text = user_text.lower().strip()

        # 1. Fast-Path Rule Based (<20ms) cho các lệnh thường gặp
        if any(w in lower_text for w in ["tắt hết", "tắt toàn bộ", "tắt cả nhà", "đi ngủ", "ra khỏi nhà"]):
            res = await self.ha_bridge.master_turn_off_all()
            cnt = res.get("turned_off_count", 0)
            msg = f"Đã tắt toàn bộ {cnt} thiết bị trong nhà cho bạn."
            for word in msg.split(" "):
                yield word + " "
                await asyncio.sleep(0.03)
            return

        # 2. Xây dựng danh sách ứng viên Provider theo thứ tự ưu tiên (Primary -> Fallbacks)
        preferred = model_preference or self.config.get("active_provider", "gemini")
        auto_fallback = self.config.get("auto_fallback", True)

        candidates = []
        if self.config.get(preferred, {}).get("api_key"):
            candidates.append(preferred)

        if auto_fallback:
            for alt in ["groq", "deepseek", "gemini", "openrouter", "custom"]:
                if alt != preferred and self.config.get(alt, {}).get("api_key"):
                    candidates.append(alt)

        if not candidates:
            local_res = await self._try_local_rule_fallback(user_text, context_room)
            if local_res:
                for word in local_res.split(" "):
                    yield word + " "
                    await asyncio.sleep(0.03)
                return
            msg = f"Tôi đã nghe: '{user_text}', nhưng hệ thống chưa có API Key AI khả dụng."
            for word in msg.split(" "):
                yield word + " "
                await asyncio.sleep(0.03)
            return

        device_ctx = self._build_device_context()
        system_instruction = SYSTEM_PROMPT_TEMPLATE.format(
            device_context=device_ctx,
            current_room=context_room or "Không xác định"
        )

        completed_successfully = False
        last_error_msg = ""

        for prov_idx, prov in enumerate(candidates):
            prov_cfg = self.config.get(prov, {})
            api_key = prov_cfg.get("api_key", "")
            model = prov_cfg.get("model", "")
            base_url = prov_cfg.get("base_url", "")

            logger.info("Attempting AI stream with [%s] (Candidate %d/%d, model: %s)...",
                        prov, prov_idx + 1, len(candidates), model)

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    if prov != "gemini":
                        if prov == "groq":
                            endpoint = "https://api.groq.com/openai/v1/chat/completions"
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                            use_model = model or "llama-3.3-70b-versatile"
                        elif prov == "deepseek":
                            endpoint = "https://api.deepseek.com/chat/completions"
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                            use_model = model or "deepseek-flash"
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
                            "stream": True,
                            "max_tokens": 200,
                            "temperature": 0.3
                        }
                        if prov == "deepseek":
                            payload["thinking"] = {"type": "disabled"}

                        accumulated_tool_calls: Dict[int, Dict[str, Any]] = {}
                        has_text = False

                        async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                            if response.status_code != 200:
                                err_body = await response.aread()
                                last_error_msg = f"{prov} HTTP {response.status_code}"
                                logger.warning("Provider '%s' returned HTTP %d: %s. Auto-falling back...",
                                               prov, response.status_code, err_body[:100].decode('utf-8', errors='replace'))
                                continue

                            async for line in response.aiter_lines():
                                line = line.strip()
                                if not line or not line.startswith("data: "):
                                    continue
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break

                                try:
                                    chunk_json = json.loads(data_str)
                                    choices = chunk_json.get("choices", [])
                                    if not choices:
                                        continue
                                    delta = choices[0].get("delta", {})

                                    if "tool_calls" in delta and delta["tool_calls"]:
                                        for tc in delta["tool_calls"]:
                                            idx = tc.get("index", 0)
                                            if idx not in accumulated_tool_calls:
                                                accumulated_tool_calls[idx] = {
                                                    "name": tc.get("function", {}).get("name", ""),
                                                    "args": ""
                                                }
                                            fn_data = tc.get("function", {})
                                            if "name" in fn_data and fn_data["name"]:
                                                accumulated_tool_calls[idx]["name"] = fn_data["name"]
                                            if "arguments" in fn_data and fn_data["arguments"]:
                                                accumulated_tool_calls[idx]["args"] += fn_data["arguments"]

                                    content_piece = delta.get("content", "")
                                    if content_piece:
                                        has_text = True
                                        yield content_piece

                                except Exception:
                                    continue

                        if accumulated_tool_calls:
                            confirmations = []
                            for idx, call in accumulated_tool_calls.items():
                                fn_name = call.get("name", "")
                                raw_args = call.get("args", "{}")
                                try:
                                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                                except Exception:
                                    args = {}
                                res_msg = await self.execute_tool(fn_name, args)
                                confirmations.append(res_msg)

                            final_msg = " ".join(confirmations) if confirmations else "Đã thực hiện xong cho bạn."
                            if has_text:
                                yield " " + final_msg
                            else:
                                for word in final_msg.split(" "):
                                    yield word + " "
                                    await asyncio.sleep(0.03)

                        completed_successfully = True
                        break

                    else:
                        norm_mod = normalize_gemini_model(model)
                        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{norm_mod}:streamGenerateContent?alt=sse"
                        headers = {
                            "x-goog-api-key": api_key,
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "system_instruction": {"parts": [{"text": system_instruction}]},
                            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
                            "tools": [{"function_declarations": self._get_ha_tools_schema_gemini()}],
                            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 200}
                        }

                        async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                            if response.status_code != 200:
                                err_body = await response.aread()
                                last_error_msg = f"Gemini HTTP {response.status_code}"
                                logger.warning("Gemini returned HTTP %d: %s. Auto-falling back to next provider...",
                                               response.status_code, err_body[:100].decode('utf-8', errors='replace'))
                                continue

                            async for line in response.aiter_lines():
                                line = line.strip()
                                if not line or not line.startswith("data: "):
                                    continue
                                try:
                                    chunk_json = json.loads(line[6:])
                                    candidates_chunk = chunk_json.get("candidates", [])
                                    if not candidates_chunk:
                                        continue
                                    parts = candidates_chunk[0].get("content", {}).get("parts", [])
                                    for p in parts:
                                        if "text" in p and p["text"]:
                                            yield p["text"]
                                        elif "functionCall" in p:
                                            fn = p["functionCall"]
                                            res_msg = await self.execute_tool(fn.get("name", ""), fn.get("args", {}))
                                            for word in res_msg.split(" "):
                                                yield word + " "
                                                await asyncio.sleep(0.03)
                                except Exception:
                                    continue

                        completed_successfully = True
                        break

            except Exception as e:
                last_error_msg = str(e)
                logger.warning("Exception with provider '%s': %s. Auto-falling back...", prov, e)
                continue

        if not completed_successfully:
            logger.error("All AI providers failed (%s). Triggering offline local rule fallback...", last_error_msg)
            local_res = await self._try_local_rule_fallback(user_text, context_room)
            if local_res:
                for word in local_res.split(" "):
                    yield word + " "
                    await asyncio.sleep(0.03)
                return
            yield f"Các máy chủ AI đều đang bận ({last_error_msg}). Vui lòng thử lại sau ít giây."
