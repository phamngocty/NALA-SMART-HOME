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
import uuid
import asyncio
import logging
import unicodedata
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx

try:
    from .groq_failover_client import GroqFailoverClient
except ImportError:
    from groq_failover_client import GroqFailoverClient

try:
    from .adaptive_memory_manager import AdaptiveMemoryManager
except ImportError:
    from adaptive_memory_manager import AdaptiveMemoryManager

logger = logging.getLogger("AIRouter")

SYSTEM_PROMPT_TEMPLATE = """Bạn là Nala - Trợ lý giọng nói và quản gia AI của hệ thống NALA Smart Home.
Nhiệm vụ của bạn:
1. Trả lời cực kỳ ngắn gọn, tự nhiên, thân thiện bằng tiếng Việt (tối đa 1-2 câu) để đọc qua loa không bị rườm rà.
2. Điều khiển thiết bị nhà thông minh bằng cách gọi các công cụ (tools) phù hợp khi người dùng yêu cầu bật/tắt thiết bị, điều chỉnh nhiệt độ máy lạnh, tắt hết toàn nhà,...
3. NGỮ CẢNH VỊ TRÍ: Người dùng đang đứng tại phòng: [{current_room}]. Nếu người dùng ra lệnh điều khiển chung chung như 'bật đèn', 'tắt quạt', 'máy lạnh 24 độ' mà không nhắc tên phòng khác, BẮT BUỘC ưu tiên chọn thiết bị thuộc phòng [{current_room}].
4. QUY TẮC CHỌN ENTITY ID: BẮT BUỘC chỉ sử dụng chính xác mã `entity_id` nằm trong dấu ngoặc tròn `(...)` ở danh sách thiết bị bên dưới (Ví dụ: `climate.150633094640317_climate`, `light.cong_tat_phong_khach_tret_den_1`). TUYỆT ĐỐI KHÔNG tự bịa hoặc tự dịch tên tiếng Việt thành entity_id giả!
5. Nếu người dùng hỏi thông tin bình thường (thời tiết, kiến thức, chào hỏi...), hãy trả lời hóm hỉnh và súc tích.
6. NGỮ CẢNH HỘI THOẠI ĐA LƯỢT: Nếu người dùng ra lệnh tiếp nối (như 'giảm xuống 2 độ', 'đổi màu xanh', 'tắt nó đi', 'còn phòng nào nữa không'), hãy dựa vào lịch sử đối thoại trước đó để thực hiện đúng thiết bị đang được đề cập.

Danh sách các thiết bị hiện có trong nhà:
{device_context}
"""

def _normalize_vn(s: str) -> str:
    if not s:
        return ""
    s = s.replace("đ", "d").replace("Đ", "d")
    nfd = unicodedata.normalize('NFD', s)
    no_marks = "".join(c for c in nfd if unicodedata.category(c) != 'Mn').lower()
    # Chuẩn hoá các từ STT hay nghe nhầm: trầm / chăn -> trần, hắc -> hắt
    no_marks = re.sub(r'\b(tram|chan)\b', 'tran', no_marks)
    no_marks = re.sub(r'\b(hac)\b', 'hat', no_marks)
    # Chuẩn hoá ty <-> ti, tỷ <-> ti
    no_marks = re.sub(r'([ptkmlnsghd])y\b', r'\1i', no_marks)
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', no_marks)
    return ' '.join(cleaned.split())

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

class ConversationSessionManager:
    """Quản lý phiên hội thoại liên tục (Continuous Dialogue) và bộ nhớ ngữ cảnh theo phong cách Xiaozhi."""
    def __init__(self, session_timeout: float = 120.0, max_history_turns: int = 8):
        self.session_timeout = session_timeout
        self.max_history_turns = max_history_turns
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def get_or_create_session(self, device_id: str) -> Dict[str, Any]:
        if not device_id:
            return {}
        now = time.time()
        session = self.sessions.get(device_id)
        if session and (now - session.get("last_active", 0) > self.session_timeout):
            logger.info("Session context for [%s] expired (>%ss), starting fresh session.", device_id, self.session_timeout)
            session = None
        if not session:
            sess_id = f"sess_{int(now)}_{uuid.uuid4().hex[:6]}"
            session = {
                "session_id": sess_id,
                "history": [],
                "created_at": now,
                "last_active": now,
                "turn_count": 0
            }
            self.sessions[device_id] = session
        return session

    def get_session_id(self, device_id: str) -> str:
        sess = self.get_or_create_session(device_id)
        return sess.get("session_id", f"sess_{int(time.time())}")

    def get_history(self, device_id: str) -> List[Dict[str, str]]:
        if not device_id:
            return []
        session = self.sessions.get(device_id)
        if not session:
            return []
        if time.time() - session.get("last_active", 0) > self.session_timeout:
            logger.info("Session context for [%s] expired (>%ss), resetting context.", device_id, self.session_timeout)
            self.sessions.pop(device_id, None)
            return []
        return list(session.get("history", []))

    def add_turn(self, device_id: str, user_text: str, assistant_text: str) -> int:
        if not device_id or not user_text or not assistant_text:
            return 0
        now = time.time()
        sess = self.get_or_create_session(device_id)
        sess["last_active"] = now
        sess["turn_count"] += 1
        sess["history"].append({"role": "user", "content": user_text})
        sess["history"].append({"role": "assistant", "content": assistant_text})
        if len(sess["history"]) > self.max_history_turns:
            sess["history"] = sess["history"][-self.max_history_turns:]
        return sess["turn_count"]

    def clear_session(self, device_id: str):
        if device_id in self.sessions:
            logger.info("Cleared conversation session for [%s]", device_id)
            self.sessions.pop(device_id, None)

    @staticmethod
    def is_farewell(text: str) -> bool:
        """Phát hiện các câu chào tạm biệt hoặc kết thúc phiên trò chuyện chuẩn xác, tránh bắt nhầm lệnh điều khiển."""
        if not text:
            return False
        normalized = _normalize_vn(text).strip()
        if not normalized:
            return False

        # 1. Chống bắt nhầm: Nếu câu có chứa từ khóa lệnh điều khiển / truy vấn nhà thông minh -> KHÔNG PHẢI tạm biệt
        action_keywords = [
            "bat", "tat", "mo", "dong", "chinh", "tang", "giam", "cai", "set",
            "den", "quat", "may lanh", "dieu hoa", "rem", "cong tac", "o cam",
            "binh nong lanh", "nhiet do", "may gio", "thoi tiet", "bao nhieu",
            "the nao", "tai sao", "la gi", "ai do", "ai day"
        ]
        norm_words = normalized.split()
        for kw in action_keywords:
            if " " in kw:
                if kw in normalized:
                    return False
            else:
                if kw in norm_words:
                    return False

        # 2. Danh sách từ khóa tạm biệt / kết thúc phiên thực sự
        farewell_keywords = [
            "tam biet", "bye", "goodbye", "cam on", "cam on nhe", "cam on ban",
            "thoi", "thoi duoc roi", "nghi di", "im di", "im lang", "het roi",
            "khong co gi", "dung lai", "khong can nua", "ok roi", "duoc roi"
        ]

        # Khớp chính xác hoàn toàn câu (Exact match)
        if normalized in farewell_keywords:
            return True

        # Nếu là câu ngắn (<= 4 từ), cho phép bắt đầu hoặc kết thúc bằng từ khóa chào
        if len(norm_words) <= 4:
            for kw in farewell_keywords:
                if normalized == kw or normalized.startswith(kw + " ") or normalized.endswith(" " + kw):
                    return True

        return False

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
        self.session_mgr = ConversationSessionManager(session_timeout=self.config.get("session_timeout_seconds", 120.0))

        groq_cfg = self.config.get("groq", {})
        self.groq_client = GroqFailoverClient(
            api_key=groq_cfg.get("api_key", ""),
            default_preferred_model=groq_cfg.get("model", "llama-3.3-70b-versatile")
        )
        self.memory_mgr = AdaptiveMemoryManager(data_dir=self.data_dir)

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
            "tts_voice": "google_fast",
            "stt_service_url": os.getenv("STT_SERVICE_URL", "http://127.0.0.1:8095/v1/audio/transcriptions"),
            "stt_provider": "auto",
            "stt_groq_model": "whisper-large-v3-turbo",
            "auto_fallback": True,
            "continuous_conversation": True,
            "continuous_timeout_ms": 8000,
            "session_timeout_seconds": 120
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
            "continuous_conversation": self.config.get("continuous_conversation", True),
            "continuous_timeout_ms": self.config.get("continuous_timeout_ms", 8000),
            "session_timeout_seconds": self.config.get("session_timeout_seconds", 120),
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
            if "continuous_conversation" in new_data:
                self.config["continuous_conversation"] = bool(new_data["continuous_conversation"])
            if "continuous_timeout_ms" in new_data:
                self.config["continuous_timeout_ms"] = int(new_data["continuous_timeout_ms"])
            if "session_timeout_seconds" in new_data:
                self.config["session_timeout_seconds"] = int(new_data["session_timeout_seconds"])
                self.session_mgr.session_timeout = self.config["session_timeout_seconds"]

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

            if hasattr(self, "groq_client"):
                g_cfg = self.config.get("groq", {})
                if g_cfg.get("api_key"):
                    self.groq_client.set_api_key(g_cfg["api_key"])
                if g_cfg.get("model"):
                    self.groq_client.default_preferred_model = g_cfg["model"]

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

    async def execute_tool(self, name: str, args: Dict[str, Any], context_room: str = "", user_text: str = "") -> str:
        """Thực thi action gọi thiết bị vào Home Assistant và học hỏi thói quen."""
        logger.info("Executing HA Tool: %s with args %s (room: %s, text: %s)", name, args, context_room, user_text)
        try:
            if name == "control_home_device":
                raw_eid = args.get("entity_id", "")
                action = args.get("action", "turn_on")
                domain = "climate" if action == "set_temperature" else (raw_eid.split(".")[0] if "." in raw_eid else "light")

                eid, friendly_name = self._resolve_real_entity_id(raw_eid, domain)

                # Ghi nhận học hỏi thói quen & biệt danh nếu có user_text
                if user_text and hasattr(self, "memory_mgr"):
                    try:
                        if self.memory_mgr.is_user_correction(user_text):
                            self.memory_mgr.learn_user_correction(user_text, eid, context_room)
                        else:
                            self.memory_mgr.learn_device_interaction(user_text, eid, context_room, domain, action)
                    except Exception as me:
                        logger.warning("Adaptive Memory learning exception: %s", me)

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
            async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=12.0) as client:
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
        """Dự phòng offline thông minh qua Home Assistant: Chuẩn hóa ngữ âm tiếng Việt & Area Matching chính xác 100%."""
        if not user_text or not self.ha_bridge:
            return None
        norm_user = _normalize_vn(user_text)

        is_turn_on = any(w in norm_user for w in ["bat", "mo", "khoi dong", "set", "chinh"])
        is_turn_off = any(w in norm_user for w in ["tat", "dong", "ngat", "dung"])
        if not is_turn_on and not is_turn_off:
            return None

        action = "turn_on" if is_turn_on else "turn_off"
        action_name = "bật" if is_turn_on else "tắt"

        # 1. Xác định domain mục tiêu
        target_domain = ""
        if any(w in norm_user for w in ["may lanh", "dieu hoa", "ac", "nhiet do"]):
            target_domain = "climate"
        elif any(w in norm_user for w in ["den", "anh sang", "led", "chieu sang"]):
            target_domain = "light"
        elif any(w in norm_user for w in ["quat", "fan"]):
            target_domain = "fan"
        elif any(w in norm_user for w in ["cong tac", "o cam"]):
            target_domain = "switch"

        # 2. Lấy danh sách entities đầy đủ có kèm Area/Phòng
        all_entities = self.ha_bridge.get_entities_list()
        if not all_entities:
            return None

        candidates = []
        for e in all_entities:
            dom = e.get("domain", "")
            if target_domain:
                if target_domain == "light":
                    if dom == "light" or (dom == "switch" and "den" in _normalize_vn(e.get("name", ""))):
                        candidates.append(e)
                elif target_domain == "fan":
                    if dom == "fan" or "quat" in _normalize_vn(e.get("name", "")):
                        candidates.append(e)
                elif dom == target_domain:
                    candidates.append(e)
            else:
                candidates.append(e)

        # 3. Phát hiện phòng đích trong câu nói
        norm_context = _normalize_vn(context_room)
        detected_room = ""
        # Duyệt qua các area đã biết trong HA
        for a_id, a_data in self.ha_bridge.areas.items():
            a_norm_name = _normalize_vn(a_data.get("name", ""))
            a_norm_id = _normalize_vn(a_id)
            if a_norm_name and len(a_norm_name) >= 4 and a_norm_name in norm_user:
                detected_room = a_norm_name
                break
            if a_norm_id and len(a_norm_id) >= 4 and a_norm_id in norm_user:
                detected_room = a_norm_id
                break

        # Khớp các cụm từ phòng thông dụng
        if not detected_room:
            for common_room in ["phong khach", "phong bep", "phong chieu", "phong ngu ti", "phong ngu me", "phong ngu tret", "ban cong", "nha xe"]:
                if common_room in norm_user:
                    detected_room = common_room
                    break

        effective_room = detected_room or norm_context

        best_entity = None
        best_score = -1

        for e in candidates:
            eid = e.get("entity_id", "")
            norm_name = _normalize_vn(e.get("name", ""))
            norm_eid = _normalize_vn(eid)
            norm_area = _normalize_vn(e.get("area_name", ""))
            norm_area_id = _normalize_vn(e.get("area_id", ""))

            score = 0
            is_room_match = False
            if effective_room:
                if effective_room in norm_area or norm_area in effective_room:
                    is_room_match = True
                    score += 50
                elif effective_room in norm_area_id or norm_area_id in effective_room:
                    is_room_match = True
                    score += 50
                elif effective_room in norm_eid:
                    is_room_match = True
                    score += 40

            # Nếu người dùng đích danh gọi tên phòng khác, loại bỏ ngay các thiết bị phòng khác
            if detected_room and not is_room_match:
                continue

            # Điểm khớp loại thiết bị con (Đèn trần / Đèn ngủ / Quạt...)
            if "tran" in norm_user and "tran" in norm_name:
                score += 30
            if "ngu" in norm_user and "ngu" in norm_name:
                score += 20
            if "chinh" in norm_user and "chinh" in norm_name:
                score += 20
            if "hat" in norm_user and "hat" in norm_name:
                score += 20
            if "ban cong" in norm_user and "ban cong" in norm_name:
                score += 25
            if "quat" in norm_user and "quat" in norm_name:
                score += 30

            for word in norm_name.split():
                if len(word) >= 3 and word in norm_user:
                    score += 5

            if is_room_match and target_domain == "light":
                if "tran" in norm_name or "1" in eid:
                    score += 10

            if score > best_score and score > 0:
                best_score = score
                best_entity = e

        if not best_entity:
            room_label = detected_room or context_room
            if room_label:
                return f"Không tìm thấy thiết bị phù hợp tại {room_label}."
            return "Không tìm thấy thiết bị nào phù hợp với yêu cầu của bạn."

        matched_eid = best_entity.get("entity_id")
        matched_name = best_entity.get("name", matched_eid)
        domain = matched_eid.split(".")[0]

        try:
            if domain == "climate":
                # Kiểm tra xem có lệnh chỉnh nhiệt độ không (ví dụ "25 độ")
                temp_match = re.search(r'\b(\d{2})\s*(do|deg|c)?\b', norm_user)
                if temp_match and is_turn_on:
                    target_temp = int(temp_match.group(1))
                    if 16 <= target_temp <= 30:
                        await self.ha_bridge.call_service("climate", "set_temperature", entity_id=matched_eid, service_data={"temperature": target_temp})
                        return f"Đã chỉnh nhiệt độ {matched_name} thành {target_temp}°C."
                if is_turn_off:
                    await self.ha_bridge.call_service("climate", "set_hvac_mode", entity_id=matched_eid, service_data={"hvac_mode": "off"})
                else:
                    await self.ha_bridge.call_service("climate", "set_hvac_mode", entity_id=matched_eid, service_data={"hvac_mode": "cool"})
            else:
                await self.ha_bridge.call_service(domain, action, entity_id=matched_eid)

            return f"Đã {action_name} {matched_name} thành công."
        except Exception as ex:
            logger.error("Local rule execution error for %s: %s", matched_eid, ex)
            return f"Lỗi điều khiển {matched_name}: {ex}"

    async def process_intent(self, user_text: str, context_room: str = "", model_preference: Optional[str] = None, device_id: Optional[str] = None) -> str:
        """Xử lý giọng nói người dùng, kết hợp Fast-Rule, Multi-AI Function Calling và Cơ chế Tự Động Dự Phòng (Failover/Fallback)."""
        if not user_text:
            return "Tôi không nghe thấy gì cả."

        # 0. Kiểm tra câu chào tạm biệt / kết thúc hội thoại
        if self.session_mgr.is_farewell(user_text):
            if device_id:
                self.session_mgr.clear_session(device_id)
            return "Dạ, tạm biệt bạn nhé! Hẹn gặp lại bạn sau."

        history = self.session_mgr.get_history(device_id) if device_id else []

        lower_text = user_text.lower().strip()

        # 1. FAST-PATH RULE BASED (<20ms) cho các lệnh thường gặp
        if any(w in lower_text for w in ["tắt hết", "tắt toàn bộ", "tắt cả nhà", "đi ngủ", "ra khỏi nhà"]):
            res = await self.ha_bridge.master_turn_off_all()
            cnt = res.get("turned_off_count", 0)
            return f"Đã tắt {cnt} thiết bị trong nhà cho bạn."

        # 1.1 FAST-PATH TỰ THÍCH ỨNG TỪ TRÍ NHỚ ĐÃ HỌC CỦA NALA (<20ms)
        fast_match = self.memory_mgr.match_fast_path(user_text, context_room)
        if fast_match:
            eid = fast_match["entity_id"]
            act = fast_match["action"]
            domain = eid.split(".")[0] if "." in eid else "light"
            logger.info("Executing Fast-Path from Learned Memory: %s.%s on %s", domain, act, eid)
            if self.ha_bridge:
                await self.ha_bridge.call_service(domain, act, entity_id=eid)
                verb = "bật" if act == "turn_on" else "tắt"
                ret = f"Đã {verb} {fast_match['phrase']} theo thói quen cho bạn."
                if device_id:
                    self.session_mgr.add_turn(device_id, user_text, ret)
                return ret

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
        learned_ctx = self.memory_mgr.get_prompt_context(context_room or "", user_text)
        system_instruction = SYSTEM_PROMPT_TEMPLATE.format(
            device_context=device_ctx + learned_ctx,
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
                async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=10.0) as client:
                    if prov == "gemini":
                        norm_mod = normalize_gemini_model(model)
                        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{norm_mod}:generateContent"
                        headers = {
                            "x-goog-api-key": api_key,
                            "Content-Type": "application/json"
                        }
                        gemini_contents = []
                        for h in history:
                            g_role = "model" if h["role"] == "assistant" else "user"
                            gemini_contents.append({"role": g_role, "parts": [{"text": h["content"]}]})
                        gemini_contents.append({"role": "user", "parts": [{"text": user_text}]})
                        payload = {
                            "system_instruction": {"parts": [{"text": system_instruction}]},
                            "contents": gemini_contents,
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
                                    res_msg = await self.execute_tool(fn.get("name", ""), fn.get("args", {}), context_room=context_room, user_text=user_text)
                                    confirmations.append(res_msg)
                                elif "text" in part:
                                    text_replies.append(part["text"].strip())

                            ret = ""
                            if confirmations:
                                ret = " ".join(confirmations)
                            elif text_replies:
                                ret = " ".join(text_replies)
                            if ret:
                                if device_id:
                                    self.session_mgr.add_turn(device_id, user_text, ret)
                                return ret
                        else:
                            last_error_desc = f"Gemini HTTP {res.status_code}"
                            logger.warning("Gemini API error %d: %s. Auto-falling back to next provider...",
                                           res.status_code, res.text[:120])
                            continue

                    elif prov == "groq":
                        openai_messages = [{"role": "system", "content": system_instruction}]
                        for h in history:
                            openai_messages.append({"role": h["role"], "content": h["content"]})
                        openai_messages.append({"role": "user", "content": user_text})

                        groq_res = await self.groq_client.chat_completion(
                            messages=openai_messages,
                            preferred_model=model,
                            tools=self._get_ha_tools_schema_openai(),
                            tool_choice="auto",
                            max_tokens=150,
                            temperature=0.4
                        )

                        if groq_res.get("success"):
                            msg = groq_res.get("message", {})
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
                                    res_msg = await self.execute_tool(fn_name, args, context_room=context_room, user_text=user_text)
                                    confirmations.append(res_msg)
                                ret = " ".join(confirmations) if confirmations else "Đã thực hiện yêu cầu cho bạn."
                                if device_id:
                                    self.session_mgr.add_turn(device_id, user_text, ret)
                                return ret

                            content = msg.get("content", "").strip()
                            if content:
                                if device_id:
                                    self.session_mgr.add_turn(device_id, user_text, content)
                                return content
                        else:
                            last_error_desc = f"Groq Failover: {groq_res.get('error')}"
                            logger.warning("Groq failover exhausted: %s. Auto-falling back to next provider...",
                                           groq_res.get('error'))
                            continue

                    else:
                        if prov == "deepseek":
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

                        openai_messages = [{"role": "system", "content": system_instruction}]
                        for h in history:
                            openai_messages.append({"role": h["role"], "content": h["content"]})
                        openai_messages.append({"role": "user", "content": user_text})

                        payload = {
                            "model": use_model,
                            "messages": openai_messages,
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
                                    res_msg = await self.execute_tool(fn_name, args, context_room=context_room, user_text=user_text)
                                    confirmations.append(res_msg)
                                ret = " ".join(confirmations) if confirmations else "Đã thực hiện yêu cầu cho bạn."
                                if device_id:
                                    self.session_mgr.add_turn(device_id, user_text, ret)
                                return ret

                            content = msg.get("content", "").strip()
                            if content:
                                if device_id:
                                    self.session_mgr.add_turn(device_id, user_text, content)
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

    async def stream_intent(self, user_text: str, context_room: str = "", model_preference: Optional[str] = None, device_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream kết quả đối thoại thời gian thực từng token với cơ chế Tự Động Dự Phòng (Failover / Fallback)."""
        if not user_text or not user_text.strip():
            yield "Tôi không nghe thấy gì cả."
            return

        # 0. Kiểm tra câu chào tạm biệt / kết thúc hội thoại
        if self.session_mgr.is_farewell(user_text):
            if device_id:
                self.session_mgr.clear_session(device_id)
            farewell_msg = "Dạ, tạm biệt bạn nhé! Hẹn gặp lại bạn sau."
            for word in farewell_msg.split(" "):
                yield word + " "
                await asyncio.sleep(0.02)
            return

        history = self.session_mgr.get_history(device_id) if device_id else []

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

        # 1.1 FAST-PATH TỰ THÍCH ỨNG TỪ TRÍ NHỚ ĐÃ HỌC CỦA NALA (Stream <20ms)
        fast_match = self.memory_mgr.match_fast_path(user_text, context_room)
        if fast_match:
            eid = fast_match["entity_id"]
            act = fast_match["action"]
            domain = eid.split(".")[0] if "." in eid else "light"
            logger.info("Executing Fast-Path from Learned Memory (Stream): %s.%s on %s", domain, act, eid)
            if self.ha_bridge:
                await self.ha_bridge.call_service(domain, act, entity_id=eid)
                verb = "bật" if act == "turn_on" else "tắt"
                msg = f"Đã {verb} {fast_match['phrase']} theo thói quen cho bạn."
                for word in msg.split(" "):
                    yield word + " "
                    await asyncio.sleep(0.02)
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
        learned_ctx = self.memory_mgr.get_prompt_context(context_room or "", user_text)
        system_instruction = SYSTEM_PROMPT_TEMPLATE.format(
            device_context=device_ctx + learned_ctx,
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
                async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=15.0) as client:
                    if prov == "groq":
                        await self.groq_client.scan_and_sync_models()
                        groq_candidates = self.groq_client.get_candidate_models(model)
                        endpoint = "https://api.groq.com/openai/v1/chat/completions"
                        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

                        openai_messages = [{"role": "system", "content": system_instruction}]
                        for h in history:
                            openai_messages.append({"role": h["role"], "content": h["content"]})
                        openai_messages.append({"role": "user", "content": user_text})

                        groq_stream_success = False
                        for g_model in groq_candidates:
                            payload = {
                                "model": g_model,
                                "messages": openai_messages,
                                "tools": self._get_ha_tools_schema_openai(),
                                "tool_choice": "auto",
                                "stream": True,
                                "max_tokens": 200,
                                "temperature": 0.3
                            }
                            accumulated_tool_calls: Dict[int, Dict[str, Any]] = {}
                            has_text = False

                            try:
                                async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                                    if response.status_code == 429:
                                        self.groq_client.mark_model_cooldown(g_model, "Stream 429 Rate Limit")
                                        continue
                                    elif response.status_code == 404 or "model_decommissioned" in (await response.aread()).decode('utf-8', 'ignore'):
                                        self.groq_client.mark_model_deprecated(g_model, "Stream 404 Decommissioned")
                                        continue
                                    elif response.status_code in [500, 502, 503, 504]:
                                        logger.warning("Groq stream HTTP %d on model '%s'. Rolling back...", response.status_code, g_model)
                                        continue
                                    elif response.status_code != 200:
                                        err_body = await response.aread()
                                        last_error_msg = f"groq HTTP {response.status_code}"
                                        logger.warning("Groq stream error %d on model '%s': %s",
                                                       response.status_code, g_model, err_body[:100].decode('utf-8', 'ignore'))
                                        break

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
                                        res_msg = await self.execute_tool(fn_name, args, context_room=context_room, user_text=user_text)
                                        confirmations.append(res_msg)

                                    final_msg = " ".join(confirmations) if confirmations else "Đã thực hiện xong cho bạn."
                                    if has_text:
                                        yield " " + final_msg
                                    else:
                                        for word in final_msg.split(" "):
                                            yield word + " "
                                            await asyncio.sleep(0.03)

                                completed_successfully = True
                                groq_stream_success = True
                                break

                            except Exception as stream_err:
                                logger.warning("Stream attempt on Groq model '%s' failed: %s. Rolling back...", g_model, stream_err)
                                continue

                        if groq_stream_success:
                            break
                        else:
                            last_error_msg = "Groq stream failover exhausted."
                            continue

                    elif prov != "gemini":
                        if prov == "deepseek":
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

                        openai_messages = [{"role": "system", "content": system_instruction}]
                        for h in history:
                            openai_messages.append({"role": h["role"], "content": h["content"]})
                        openai_messages.append({"role": "user", "content": user_text})

                        payload = {
                            "model": use_model,
                            "messages": openai_messages,
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
                                res_msg = await self.execute_tool(fn_name, args, context_room=context_room, user_text=user_text)
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
                        gemini_contents = []
                        for h in history:
                            g_role = "model" if h["role"] == "assistant" else "user"
                            gemini_contents.append({"role": g_role, "parts": [{"text": h["content"]}]})
                        gemini_contents.append({"role": "user", "parts": [{"text": user_text}]})

                        payload = {
                            "system_instruction": {"parts": [{"text": system_instruction}]},
                            "contents": gemini_contents,
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
                                            res_msg = await self.execute_tool(fn.get("name", ""), fn.get("args", {}), context_room=context_room, user_text=user_text)
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
