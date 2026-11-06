"""
NALA SMART HOME - ADVANCED AI AGENT ROUTER
Multi-provider support: Google Gemini, DeepSeek, OpenRouter (9 Router), Custom OpenAI.
Includes dynamic Home Assistant function calling & tool execution.
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
3. Nếu người dùng hỏi thông tin bình thường (thời tiết, kiến thức, chào hỏi...), hãy trả lời hóm hỉnh và súc tích.

Danh sách các thiết bị hiện có trong nhà:
{device_context}
"""

def mask_key(k: Optional[str]) -> str:
    if not k:
        return ""
    if len(k) <= 8:
        return "****"
    return f"{k[:4]}...{k[-4:]}"

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
                "model": "gemini-2.0-flash",
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai"
            },
            "deepseek": {
                "api_key": default_deepseek or os.getenv("DEEPSEEK_API_KEY", ""),
                "model": "deepseek-chat",
                "base_url": "https://api.deepseek.com/v1"
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
                    # Merge deep
                    for k, v in saved.items():
                        if isinstance(v, dict) and k in default_cfg and isinstance(default_cfg[k], dict):
                            default_cfg[k].update(v)
                        else:
                            default_cfg[k] = v
                logger.info("Loaded AI Router config from %s", self.config_file)
            except Exception as e:
                logger.error("Failed to read %s: %s", self.config_file, e)

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
                "model": self.config["gemini"].get("model", "gemini-2.0-flash"),
                "base_url": self.config["gemini"].get("base_url", "https://generativelanguage.googleapis.com/v1beta/openai")
            },
            "deepseek": {
                "api_key_masked": mask_key(self.config["deepseek"].get("api_key")),
                "has_key": bool(self.config["deepseek"].get("api_key")),
                "model": self.config["deepseek"].get("model", "deepseek-chat"),
                "base_url": self.config["deepseek"].get("base_url", "https://api.deepseek.com/v1")
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
                        self.config[prov]["model"] = p_data["model"].strip()
                    if "base_url" in p_data and p_data["base_url"]:
                        self.config[prov]["base_url"] = p_data["base_url"].strip()

                    new_key = p_data.get("api_key", "").strip()
                    # Nếu có key mới và không phải dạng masked "..."
                    if new_key and "..." not in new_key and "****" not in new_key:
                        self.config[prov]["api_key"] = new_key

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            logger.info("Saved AI configuration successfully to %s", self.config_file)
            return True
        except Exception as e:
            logger.error("Failed to save AI config: %s", e)
            return False

    def _get_ha_tools_schema(self) -> List[Dict[str, Any]]:
        """Khai báo function calling tools theo chuẩn OpenAI cho các AI models."""
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

        # Giới hạn tối đa 50 thiết bị để không làm tràn context
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
        """Test latency và kết nối đến AI provider được chỉ định."""
        t0 = time.time()
        prov_cfg = self.config.get(provider, {})
        key = api_key or prov_cfg.get("api_key", "")
        mod = model or prov_cfg.get("model", "")
        url = base_url or prov_cfg.get("base_url", "")

        if not key:
            return {"status": "error", "message": f"Chưa có API Key cho {provider}"}

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://nalasmarthome.local"
            headers["X-Title"] = "NALA Smart Home Hub"

        endpoint = f"{url.rstrip('/')}/chat/completions"
        payload = {
            "model": mod,
            "messages": [
                {"role": "user", "content": "Trả lời 'OK' nếu bạn nhận được tin này."}
            ],
            "max_tokens": 10
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(endpoint, headers=headers, json=payload)
                elapsed = int((time.time() - t0) * 1000)
                if res.status_code == 200:
                    data = res.json()
                    reply = data["choices"][0]["message"]["content"].strip()
                    return {
                        "status": "success",
                        "latency_ms": elapsed,
                        "reply": reply,
                        "model": mod,
                        "provider": provider
                    }
                else:
                    return {
                        "status": "error",
                        "http_code": res.status_code,
                        "message": res.text[:200],
                        "latency_ms": elapsed
                    }
        except Exception as e:
            elapsed = int((time.time() - t0) * 1000)
            return {"status": "error", "message": str(e), "latency_ms": elapsed}

    async def process_intent(self, user_text: str, model_preference: Optional[str] = None) -> str:
        """Xử lý giọng nói người dùng, kết hợp Rule-based cực nhanh và Multi-AI Tool Calling."""
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
            # Fallback sang provider nào đang có key
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

        # Chuẩn bị system prompt với ngữ cảnh thiết bị thực tế
        device_ctx = self._build_device_context()
        system_instruction = SYSTEM_PROMPT_TEMPLATE.format(device_context=device_ctx)
        tools = self._get_ha_tools_schema()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        if prov == "openrouter":
            headers["HTTP-Referer"] = "https://nalasmarthome.local"
            headers["X-Title"] = "NALA Smart Home Hub"

        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_text}
            ],
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": 150,
            "temperature": 0.4
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(endpoint, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    msg = data["choices"][0]["message"]

                    # Kiểm tra xem Model có gọi Tool không
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

                        # Trả về câu xác nhận hành động
                        if confirmations:
                            return " ".join(confirmations)
                        return "Đã thực hiện yêu cầu cho bạn."

                    # Không gọi tool -> trả lời tự nhiên
                    content = msg.get("content", "").strip()
                    if content:
                        return content
                else:
                    logger.error("AI Provider %s error %d: %s", prov, res.status_code, res.text)
                    return f"Xin lỗi, {prov} báo lỗi ({res.status_code})."

        except Exception as e:
            logger.error("Error communicating with AI Provider %s: %s", prov, e)

        return "Xin lỗi, hiện tại tôi gặp sự cố khi kết nối tới trợ lý AI."
