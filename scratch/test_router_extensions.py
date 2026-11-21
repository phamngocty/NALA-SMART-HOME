import sys
import os
sys.path.insert(0, os.path.abspath("."))

import asyncio
from unittest.mock import MagicMock
from server_nas_hub.app.ai_agent_router import AIAgentRouter

async def test_router_extensions():
    ha_mock = MagicMock()
    ha_mock.entities = {
        "light.den_phong_khach": {"state": "off", "attributes": {"friendly_name": "Đèn Phòng Khách"}},
        "media_player.loa_phong_khach": {"state": "idle", "attributes": {"friendly_name": "Loa Phòng Khách"}}
    }
    ha_mock.call_service = MagicMock(return_value=asyncio.Future())
    ha_mock.call_service.return_value.set_result(True)

    router = AIAgentRouter("fake_gemini", "fake_deepseek", ha_mock, data_dir="scratch/test_data")
    
    # Check safe config
    cfg = router.get_safe_config()
    print("Extensions in safe config:", "extensions" in cfg)
    assert "extensions" in cfg
    assert cfg["extensions"]["weather_enabled"] is True

    # Check OpenAI tools schema
    tools_openai = router._get_ha_tools_schema_openai()
    tool_names = [t["function"]["name"] for t in tools_openai]
    print("OpenAI tools:", tool_names)
    assert "get_weather" in tool_names
    assert "web_search" in tool_names
    assert "play_music" in tool_names

    # Check Gemini tools schema
    tools_gemini = router._get_ha_tools_schema_gemini()
    gem_names = [t["name"] for t in tools_gemini]
    print("Gemini tools:", gem_names)
    assert "get_weather" in gem_names

    # Test executing tool get_weather
    w_res = await router.execute_tool("get_weather", {"location": "Đà Nẵng"})
    print("Weather tool result:", w_res)
    assert "Đà Nẵng" in w_res

    # Test executing tool play_music
    m_res = await router.execute_tool("play_music", {"song_name": "Em Của Ngày Hôm Qua", "room": "Phòng Khách"}, context_room="Phòng Khách")
    print("Music tool result:", m_res)
    assert "Em Của Ngày Hôm Qua" in m_res

    print("\n✅ All AIAgentRouter extension tests PASSED!")

if __name__ == "__main__":
    asyncio.run(test_router_extensions())
