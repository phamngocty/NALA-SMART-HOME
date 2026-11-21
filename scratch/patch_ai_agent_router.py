import sys

with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add import ExtensionMCPService
import_target = """try:
    from .adaptive_memory_manager import AdaptiveMemoryManager
except ImportError:
    from adaptive_memory_manager import AdaptiveMemoryManager"""

import_replacement = """try:
    from .adaptive_memory_manager import AdaptiveMemoryManager
except ImportError:
    from adaptive_memory_manager import AdaptiveMemoryManager

try:
    from .extension_mcp_service import ExtensionMCPService
except ImportError:
    from extension_mcp_service import ExtensionMCPService"""

assert import_target in code, "import_target not found"
code = code.replace(import_target, import_replacement, 1)

# 2. Add extensions to _load_initial_config
init_cfg_target = """"tts_voice": "google_fast","""
init_cfg_replacement = """"extensions": {
                "weather_enabled": True,
                "weather_location": "Hà Nội",
                "search_enabled": True,
                "music_enabled": True,
                "music_default_player": "",
                "mcp_enabled": False,
                "mcp_endpoint": ""
            },
            "tts_voice": "google_fast","""

assert init_cfg_target in code, "init_cfg_target not found"
code = code.replace(init_cfg_target, init_cfg_replacement, 1)

# 3. Initialize extension_service in AIAgentRouter.__init__
init_target = """self.memory_mgr = AdaptiveMemoryManager(data_dir=self.data_dir)"""
init_replacement = """self.memory_mgr = AdaptiveMemoryManager(data_dir=self.data_dir)
        self.extension_service = ExtensionMCPService(self.config.get("extensions", {}))"""

assert init_target in code, "init_target not found"
code = code.replace(init_target, init_replacement, 1)

# 4. Add extensions to get_safe_config
safe_target = """"session_timeout_seconds": self.config.get("session_timeout_seconds", 120),"""
safe_replacement = """"session_timeout_seconds": self.config.get("session_timeout_seconds", 120),
            "extensions": self.config.get("extensions", {
                "weather_enabled": True,
                "weather_location": "Hà Nội",
                "search_enabled": True,
                "music_enabled": True,
                "music_default_player": "",
                "mcp_enabled": False,
                "mcp_endpoint": ""
            }),"""

assert safe_target in code, "safe_target not found"
code = code.replace(safe_target, safe_replacement, 1)

# 5. Add extensions saving in save_config
save_target = """if "auto_fallback" in new_data:
                self.config["auto_fallback"] = bool(new_data["auto_fallback"])"""

save_replacement = """if "auto_fallback" in new_data:
                self.config["auto_fallback"] = bool(new_data["auto_fallback"])
            if "extensions" in new_data and isinstance(new_data["extensions"], dict):
                cur_ext = self.config.setdefault("extensions", {})
                cur_ext.update(new_data["extensions"])
                if hasattr(self, "extension_service"):
                    self.extension_service.config = cur_ext"""

assert save_target in code, "save_target not found"
code = code.replace(save_target, save_replacement, 1)

# 6. Append extension tools to _get_ha_tools_schema_openai
openai_tools_end = """                        "required": ["scene_id"]
                    }
                }
            }
        ]"""

openai_tools_replacement = """                        "required": ["scene_id"]
                    }
                }
            }
        ]
        if hasattr(self, "extension_service"):
            ext_tools = self.extension_service.get_extension_tools_openai()
            ha_tools.extend(ext_tools)
        return ha_tools"""

# We need ha_tools variable
code = code.replace("""def _get_ha_tools_schema_openai(self) -> List[Dict[str, Any]]:
        \"\"\"Khai báo function calling tools theo chuẩn OpenAI (cho DeepSeek, OpenRouter).\"\"\"
        return [""", """def _get_ha_tools_schema_openai(self) -> List[Dict[str, Any]]:
        \"\"\"Khai báo function calling tools theo chuẩn OpenAI (cho DeepSeek, OpenRouter).\"\"\"
        ha_tools = [""", 1)

assert openai_tools_end in code, "openai_tools_end not found"
code = code.replace(openai_tools_end, openai_tools_replacement, 1)

# 7. Append extension tools to _get_ha_tools_schema_gemini
code = code.replace("""def _get_ha_tools_schema_gemini(self) -> List[Dict[str, Any]]:
        \"\"\"Khai báo function declarations theo chuẩn Google Gemini REST.\"\"\"
        return [""", """def _get_ha_tools_schema_gemini(self) -> List[Dict[str, Any]]:
        \"\"\"Khai báo function declarations theo chuẩn Google Gemini REST.\"\"\"
        gemini_tools = [""", 1)

gemini_tools_end = """                    "required": ["scene_id"]
                }
            }
        ]"""

gemini_tools_replacement = """                    "required": ["scene_id"]
                }
            }
        ]
        if hasattr(self, "extension_service"):
            ext_tools = self.extension_service.get_extension_tools_gemini()
            gemini_tools.extend(ext_tools)
        return gemini_tools"""

assert gemini_tools_end in code, "gemini_tools_end not found"
code = code.replace(gemini_tools_end, gemini_tools_replacement, 1)

# 8. Add extension tool handlers in execute_tool
execute_target = """            elif name == "activate_scene":
                sid = args.get("scene_id", "")
                await self.ha_bridge.call_service("scene", "turn_on", sid)
                return f"Đã kích hoạt ngữ cảnh {sid}." """

# Let's find exact activate_scene in code
idx_scene = code.find('elif name == "activate_scene":')
assert idx_scene != -1, "activate_scene not found in execute_tool"

idx_scene_end = code.find('return f"Đã kích hoạt ngữ cảnh {sid}."', idx_scene)
assert idx_scene_end != -1, "return activate_scene not found"

end_statement = 'return f"Đã kích hoạt ngữ cảnh {sid}."'
idx_insert = idx_scene_end + len(end_statement)

extension_execution_code = """

            elif name == "get_weather":
                loc = args.get("location", "")
                return await self.extension_service.get_weather(loc)

            elif name == "web_search":
                query = args.get("query", "")
                return await self.extension_service.web_search(query)

            elif name == "play_music":
                song = args.get("song_name", "")
                artist = args.get("artist", "")
                room = args.get("room", "") or context_room
                return await self.extension_service.play_music(song, artist, room, ha_bridge=self.ha_bridge)

            elif name == "control_media":
                action = args.get("action", "play")
                room = args.get("room", "") or context_room
                return await self.extension_service.control_media(action, room, ha_bridge=self.ha_bridge)

            elif hasattr(self, "extension_service") and self.config.get("extensions", {}).get("mcp_enabled"):
                mcp_url = self.config.get("extensions", {}).get("mcp_endpoint", "")
                if mcp_url:
                    return await self.extension_service.call_mcp_tool(mcp_url, name, args)"""

code = code[:idx_insert] + extension_execution_code + code[idx_insert:]

with open('server_nas_hub/app/ai_agent_router.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("✅ Successfully patched server_nas_hub/app/ai_agent_router.py with ExtensionMCPService!")
