"""
NALA SMART HOME - EXTENSION & MCP SERVICE
Integrates XiaoZhi-style Official Services (Weather, Online Search, Music Player)
and Custom Services (Model Context Protocol - MCP Endpoint).
"""

import re
import json
import logging
import asyncio
import urllib.parse
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger("ExtensionMCPService")

WMO_WEATHER_MAP = {
    0: "Trời quang, nắng đẹp",
    1: "Trời ít mây, thoáng đãng",
    2: "Trời mây rải rác",
    3: "Trời nhiều mây, râm mát",
    45: "Có sương mù nhẹ",
    48: "Có sương mù dày hạt",
    51: "Mưa phùn nhẹ rải rác",
    53: "Mưa phùn vừa",
    55: "Mưa phùn hạt nặng",
    56: "Mưa phùn lạnh",
    57: "Mưa phùn lạnh hạt nặng",
    61: "Có mưa rào nhỏ",
    63: "Có mưa rào vừa",
    65: "Có mưa to diện rộng",
    66: "Mưa rào lạnh buốt",
    67: "Mưa to buốt giá",
    71: "Tuyết rơi nhẹ",
    73: "Tuyết rơi vừa",
    75: "Tuyết rơi dày",
    80: "Mưa rào thoáng qua",
    81: "Mưa rào lượng vừa",
    82: "Mưa rào xối xả rất to",
    85: "Mưa tuyết nhẹ",
    86: "Mưa tuyết nặng hạt",
    95: "Có dông sét, mưa dông",
    96: "Có dông kèm mưa đá nhỏ",
    99: "Có dông mạnh kèm mưa đá lớn"
}

VIETNAMESE_CITY_COORDINATES = {
    "ha noi": (21.0285, 105.8542),
    "hanoi": (21.0285, 105.8542),
    "ho chi minh": (10.8231, 106.6297),
    "tp hcm": (10.8231, 106.6297),
    "sai gon": (10.8231, 106.6297),
    "da nang": (16.0544, 108.2022),
    "hai phong": (20.8449, 106.6881),
    "can tho": (10.0452, 105.7469),
    "nha trang": (12.2388, 109.1967),
    "da lat": (11.9404, 108.4583),
    "hue": (16.4637, 107.5909),
    "vung tau": (10.3460, 107.0843),
    "quang ninh": (20.9505, 107.0734)
}

class ExtensionMCPService:
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self.config = config_dict or {}
        self._cached_mcp_tools: List[Dict[str, Any]] = []

    # =========================================================================
    # 1. THỜI TIẾT (OPEN-METEO 100% MIỄN PHÍ)
    # =========================================================================
    async def get_weather(self, location: str = "") -> str:
        """Tra cứu thời tiết thời gian thực qua Open-Meteo API (không cần API key)."""
        loc = (location or self.config.get("weather_location", "Hà Nội")).strip()
        loc_normalized = loc.lower().replace("thành phố ", "").replace("tp. ", "").replace("tp ", "").strip()
        
        lat, lon = None, None
        for city_key, coords in VIETNAMESE_CITY_COORDINATES.items():
            if city_key in loc_normalized or loc_normalized in city_key:
                lat, lon = coords
                break

        # Nếu không có trong danh mục sẵn có, gọi Geocoding API
        if lat is None:
            try:
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(loc)}&count=1&language=vi&format=json"
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(geo_url, headers={"User-Agent": "NALA-Hub/3.2.0"})
                    if resp.status_code == 200:
                        geo_data = resp.json()
                        results = geo_data.get("results", [])
                        if results:
                            lat = results[0]["latitude"]
                            lon = results[0]["longitude"]
            except Exception as e:
                logger.warning("[Extension] Geocoding error for '%s': %s", loc, e)

        # Fallback về Hà Nội nếu vẫn chưa tìm ra toạ độ
        if lat is None or lon is None:
            lat, lon = 21.0285, 105.8542
            loc = "Hà Nội"

        try:
            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
                f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(weather_url, headers={"User-Agent": "NALA-Hub/3.2.0"})
                if res.status_code != 200:
                    return f"Dạ, hiện không thể kết nối tới dịch vụ thời tiết cho {loc}."
                data = res.json()

            current = data.get("current", {})
            daily = data.get("daily", {})

            temp = current.get("temperature_2m")
            apparent_temp = current.get("apparent_temperature", temp)
            humidity = current.get("relative_humidity_2m", 0)
            wind = current.get("wind_speed_10m", 0)
            w_code = current.get("weather_code", 0)
            desc = WMO_WEATHER_MAP.get(w_code, "Thời tiết bình thường")

            max_temp = daily.get("temperature_2m_max", [temp])[0]
            min_temp = daily.get("temperature_2m_min", [temp])[0]
            rain_prob = daily.get("precipitation_probability_max", [0])[0]

            return (
                f"Thời tiết tại {loc} hiện tại: {temp}°C (cảm giác như {apparent_temp}°C), {desc}, "
                f"độ ẩm {humidity}%, gió {wind} km/h. "
                f"Dự báo hôm nay: cao nhất {max_temp}°C, thấp nhất {min_temp}°C, xác suất mưa {rain_prob}%."
            )
        except Exception as e:
            logger.error("[Extension] Weather fetch error: %s", e)
            return f"Dạ, em gặp sự cố khi tra cứu thời tiết cho {loc}."

    # =========================================================================
    # 2. TÌM KIẾM TRỰC TUYẾN (DUCKDUCKGO & WIKIPEDIA 100% MIỄN PHÍ)
    # =========================================================================
    async def web_search(self, query: str) -> str:
        """Tìm kiếm thông tin thời gian thực qua Google News RSS, Wikipedia Tiếng Việt và DuckDuckGo (100% Miễn phí)."""
        import xml.etree.ElementTree as ET
        q = (query or "").strip()
        if not q:
            return "Không có từ khóa tìm kiếm."

        results = []

        # 1. Tra cứu tin tức thời gian thực, giá cả, sự kiện mới nhất qua Google News VN RSS
        try:
            rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=vi&gl=VN&ceid=VN:vi"
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(rss_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    items = root.findall(".//item")
                    if items:
                        for it in items[:3]:
                            t_node = it.find("title")
                            if t_node is not None and t_node.text:
                                results.append(t_node.text.strip())
        except Exception as e:
            logger.debug("[Extension] Google News RSS search error: %s", e)

        # 2. Tra cứu bách khoa Wikipedia Tiếng Việt
        try:
            wiki_search_url = f"https://vi.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&utf8=&format=json"
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(wiki_search_url, headers={"User-Agent": "NALA-Hub/3.2.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    search_items = data.get("query", {}).get("search", [])
                    if search_items:
                        top = search_items[0]
                        title = top.get("title", "")
                        snippet = re.sub(r'<[^>]+>', '', top.get("snippet", "")).strip()
                        if snippet:
                            results.append(f"{title}: {snippet}")
        except Exception as e:
            logger.debug("[Extension] Wikipedia search error: %s", e)

        # 3. Thử DuckDuckGo Instant Answer
        if not results:
            try:
                ddg_api = f"https://api.duckduckgo.com/?q={urllib.parse.quote(q)}&format=json&no_html=1&skip_disambig=1"
                async with httpx.AsyncClient(timeout=3.5) as client:
                    resp = await client.get(ddg_api, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                    if resp.status_code == 200:
                        data = resp.json()
                        abstract = data.get("AbstractText", "").strip()
                        if abstract:
                            results.append(abstract)
            except Exception as e:
                logger.debug("[Extension] DDG error: %s", e)

        if results:
            return "[Thông tin thời gian thực]: " + " | ".join(results)

        return f"Dạ, em đã tìm kiếm về '{q}' nhưng chưa có dữ liệu tóm tắt phù hợp."

    # =========================================================================
    # 3. ÂM NHẠC & ĐA PHƯƠNG TIỆN (HOME ASSISTANT MEDIA PLAYER)
    # =========================================================================
    async def play_music(self, song_name: str, artist: str = "", room: str = "", ha_bridge = None) -> str:
        """Phát nhạc qua loa Home Assistant (Media Player / Spotify / Music Assistant)."""
        song = (song_name or "").strip()
        if not song:
            return "Bạn muốn nghe bài hát nào ạ?"

        query_full = f"{song} {artist}".strip()
        player_entity = None
        friendly_player = "loa thông minh"

        if ha_bridge:
            # Tìm media_player trong phòng hoặc lấy media_player mặc định
            all_media_players = [
                eid for eid in ha_bridge.entities.keys()
                if eid.startswith("media_player.")
            ]

            # 1. Ưu tiên player có tên phòng trùng khớp
            if room:
                room_norm = room.lower().replace("phòng ", "").strip()
                for eid in all_media_players:
                    f_name = ha_bridge.entities[eid].get("attributes", {}).get("friendly_name", "").lower()
                    if room_norm in f_name or room_norm in eid.lower():
                        player_entity = eid
                        friendly_player = ha_bridge.entities[eid].get("attributes", {}).get("friendly_name", eid)
                        break

            # 2. Nếu không tìm thấy, lấy default_media_player trong config
            if not player_entity:
                cfg_player = self.config.get("music_default_player", "")
                if cfg_player and cfg_player in ha_bridge.entities:
                    player_entity = cfg_player
                    friendly_player = ha_bridge.entities[cfg_player].get("attributes", {}).get("friendly_name", cfg_player)

            # 3. Nếu vẫn chưa có, lấy player đầu tiên đang mở hoặc khả dụng
            if not player_entity and all_media_players:
                player_entity = all_media_players[0]
                friendly_player = ha_bridge.entities[player_entity].get("attributes", {}).get("friendly_name", player_entity)

            if player_entity:
                try:
                    await ha_bridge.call_service(
                        "media_player",
                        "play_media",
                        entity_id=player_entity,
                        service_data={
                            "media_content_id": query_full,
                            "media_content_type": "music"
                        }
                    )
                    return f"Dạ, đang phát bài '{song}' trên {friendly_player} cho bạn."
                except Exception as e:
                    logger.warning("[Extension] Error calling play_media on %s: %s", player_entity, e)
                    return f"Dạ, em đã nhận lệnh mở '{song}', nhưng loa {friendly_player} phản hồi lỗi."

        return f"Dạ, em đã ghi nhận muốn mở bài '{song}', nhưng nhà mình chưa cài đặt loa Media Player tương thích."

    async def control_media(self, action: str, room: str = "", ha_bridge = None) -> str:
        """Điều khiển phát/dừng/tăng giảm âm lượng media player."""
        act = (action or "play").lower().strip()
        player_entity = None
        friendly_player = "loa"

        if ha_bridge:
            all_media_players = [
                eid for eid in ha_bridge.entities.keys()
                if eid.startswith("media_player.")
            ]
            cfg_player = self.config.get("music_default_player", "")
            if cfg_player and cfg_player in ha_bridge.entities:
                player_entity = cfg_player
                friendly_player = ha_bridge.entities[cfg_player].get("attributes", {}).get("friendly_name", cfg_player)
            elif all_media_players:
                player_entity = all_media_players[0]
                friendly_player = ha_bridge.entities[player_entity].get("attributes", {}).get("friendly_name", player_entity)

            if player_entity:
                service_map = {
                    "pause": ("media_player", "media_pause", "Đã tạm dừng phát nhạc."),
                    "play": ("media_player", "media_play", "Đã tiếp tục phát nhạc."),
                    "toggle": ("media_player", "media_play_pause", "Đã đổi trạng thái phát nhạc."),
                    "stop": ("media_player", "media_stop", "Đã dừng phát nhạc."),
                    "next": ("media_player", "media_next_track", "Đã chuyển bài tiếp theo."),
                    "previous": ("media_player", "media_previous_track", "Đã quay lại bài trước."),
                    "volume_up": ("media_player", "volume_up", "Đã tăng âm lượng loa."),
                    "volume_down": ("media_player", "volume_down", "Đã giảm âm lượng loa.")
                }
                if act in service_map:
                    domain, srv, msg = service_map[act]
                    await ha_bridge.call_service(domain, srv, entity_id=player_entity)
                    return msg

        return "Không tìm thấy loa đang phát để điều khiển."

    # =========================================================================
    # 4. ĐIỂM CUỐI MCP (MODEL CONTEXT PROTOCOL)
    # =========================================================================
    async def test_mcp_server(self, endpoint_url: str) -> Dict[str, Any]:
        """Kiểm tra kết nối và quét danh sách công cụ (tools) từ MCP Server."""
        url = (endpoint_url or "").strip()
        if not url:
            return {"status": "error", "message": "Vui lòng nhập URL MCP Server"}

        try:
            rpc_payload = {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/list",
                "params": {}
            }
            async with httpx.AsyncClient(timeout=6.0) as client:
                t0 = asyncio.get_event_loop().time()
                resp = await client.post(url, json=rpc_payload, headers={"Content-Type": "application/json"})
                latency_ms = int((asyncio.get_event_loop().time() - t0) * 1000)

                if resp.status_code == 200:
                    data = resp.json()
                    tools = data.get("result", {}).get("tools", [])
                    self._cached_mcp_tools = tools
                    return {
                        "status": "success",
                        "latency_ms": latency_ms,
                        "tool_count": len(tools),
                        "tools": tools,
                        "message": f"Kết nối thành công ({latency_ms}ms)! Tìm thấy {len(tools)} công cụ MCP."
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Máy chủ MCP phản hồi mã lỗi HTTP {resp.status_code}"
                    }
        except Exception as e:
            logger.warning("[Extension] MCP test error: %s", e)
            return {"status": "error", "message": f"Không thể kết nối máy chủ MCP: {str(e)}"}

    async def call_mcp_tool(self, endpoint_url: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Thực thi gọi công cụ tùy biến qua giao thức MCP JSON-RPC."""
        url = (endpoint_url or self.config.get("mcp_endpoint", "")).strip()
        if not url:
            return "Chưa cấu hình URL máy chủ MCP."

        rpc_payload = {
            "jsonrpc": "2.0",
            "id": "call_1",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=rpc_payload, headers={"Content-Type": "application/json"})
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("result", {}).get("content", [])
                    res_texts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            res_texts.append(item.get("text", ""))
                        elif isinstance(item, str):
                            res_texts.append(item)
                    if res_texts:
                        return "\n".join(res_texts)
                    return f"Thực thi công cụ MCP '{tool_name}' hoàn tất."
                else:
                    return f"Lỗi gọi công cụ MCP (HTTP {resp.status_code})."
        except Exception as e:
            logger.error("[Extension] MCP call_tool error: %s", e)
            return f"Không thể kết nối đến máy chủ MCP khi gọi '{tool_name}'."

    # =========================================================================
    # 5. CÔNG CỤ SCHEMAS CHO LLM (OPENAI & GEMINI)
    # =========================================================================
    def get_extension_tools_openai(self) -> List[Dict[str, Any]]:
        """Sinh danh sách Function Calling Tools theo chuẩn OpenAI."""
        tools = []
        if self.config.get("weather_enabled", True):
            tools.append({
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Tra cứu thông tin thời tiết hiện tại, nhiệt độ, độ ẩm, khả năng mưa theo địa điểm.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "Tên thành phố hoặc tỉnh thành cần xem thời tiết (ví dụ: Hà Nội, Hồ Chí Minh, Đà Nẵng, Hải Phòng)."
                            }
                        },
                        "required": []
                    }
                }
            })

        if self.config.get("search_enabled", True):
            tools.append({
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Tìm kiếm thông tin trực tuyến trên mạng (tin tức, giá cả, sự kiện, kiến thức mới).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Từ khóa tìm kiếm trên web."
                            }
                        },
                        "required": ["query"]
                    }
                }
            })

        if self.config.get("music_enabled", True):
            tools.append({
                "type": "function",
                "function": {
                    "name": "play_music",
                    "description": "Phát bài hát hoặc thể loại âm nhạc yêu cầu qua loa thông minh trong nhà.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "song_name": {
                                "type": "string",
                                "description": "Tên bài hát, ca khúc hoặc thể loại nhạc (ví dụ: Cắt Đôi Nỗi Sầu, Nhạc Trẻ, Nhạc Thư Giãn)."
                            },
                            "artist": {
                                "type": "string",
                                "description": "Tên ca sĩ hoặc nhạc sĩ thể hiện nếu có."
                            },
                            "room": {
                                "type": "string",
                                "description": "Tên phòng muốn phát nhạc (ví dụ: Phòng khách, Phòng ngủ)."
                            }
                        },
                        "required": ["song_name"]
                    }
                }
            })
            tools.append({
                "type": "function",
                "function": {
                    "name": "control_media",
                    "description": "Điều khiển phát nhạc (tạm dừng, tiếp tục, chuyển bài, dừng hẳn, tăng/giảm âm lượng).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["pause", "play", "toggle", "stop", "next", "previous", "volume_up", "volume_down"],
                                "description": "Hành động điều khiển loa."
                            },
                            "room": {
                                "type": "string",
                                "description": "Tên phòng cần điều khiển loa."
                            }
                        },
                        "required": ["action"]
                    }
                }
            })

        # Nạp thêm các tool từ MCP Server nếu đang bật MCP
        if self.config.get("mcp_enabled", False) and self._cached_mcp_tools:
            for t in self._cached_mcp_tools:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name", ""),
                        "description": t.get("description", ""),
                        "parameters": t.get("inputSchema", {"type": "object", "properties": {}})
                    }
                })

        return tools

    def get_extension_tools_gemini(self) -> List[Dict[str, Any]]:
        """Sinh danh sách Function Declarations theo chuẩn Google Gemini."""
        tools = []
        if self.config.get("weather_enabled", True):
            tools.append({
                "name": "get_weather",
                "description": "Tra cứu thời tiết, nhiệt độ, độ ẩm hiện tại và dự báo theo địa điểm.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "location": {
                            "type": "STRING",
                            "description": "Tên thành phố (ví dụ: Hà Nội, Hồ Chí Minh, Đà Nẵng)."
                        }
                    }
                }
            })

        if self.config.get("search_enabled", True):
            tools.append({
                "name": "web_search",
                "description": "Tìm kiếm thông tin kiến thức, tin tức trên web theo từ khóa.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "Từ khóa tìm kiếm."
                        }
                    },
                    "required": ["query"]
                }
            })

        if self.config.get("music_enabled", True):
            tools.append({
                "name": "play_music",
                "description": "Phát bài hát hoặc thể loại âm nhạc yêu cầu trên loa thông minh.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "song_name": {
                            "type": "STRING",
                            "description": "Tên bài hát, ca khúc hoặc thể loại nhạc."
                        },
                        "artist": {
                            "type": "STRING",
                            "description": "Tên ca sĩ thể hiện."
                        },
                        "room": {
                            "type": "STRING",
                            "description": "Tên phòng muốn phát nhạc."
                        }
                    },
                    "required": ["song_name"]
                }
            })
            tools.append({
                "name": "control_media",
                "description": "Điều khiển phát nhạc (tạm dừng, tiếp tục, chuyển bài, tăng/giảm âm lượng).",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {
                            "type": "STRING",
                            "description": "Hành động (pause, play, stop, next, previous, volume_up, volume_down)."
                        },
                        "room": {
                            "type": "STRING",
                            "description": "Tên phòng."
                        }
                    },
                    "required": ["action"]
                }
            })

        return tools
