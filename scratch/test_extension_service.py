import sys
import os
sys.path.insert(0, os.path.abspath("."))

import asyncio
from server_nas_hub.app.extension_mcp_service import ExtensionMCPService

async def run_tests():
    svc = ExtensionMCPService({
        "weather_enabled": True,
        "weather_location": "Hà Nội",
        "search_enabled": True,
        "music_enabled": True
    })

    print("1. Testing Weather Service:")
    weather_res = await svc.get_weather("Hà Nội")
    print(" ->", weather_res)
    assert "Hà Nội" in weather_res and "°C" in weather_res, "Weather failed"

    print("\n2. Testing Web Search Service:")
    search_res = await svc.web_search("Hồ Gươm")
    print(" ->", search_res)
    assert len(search_res) > 20, "Search failed"

    print("\n3. Testing OpenAI Tools Schema:")
    tools = svc.get_extension_tools_openai()
    tool_names = [t["function"]["name"] for t in tools]
    print(" -> Extension tool names:", tool_names)
    assert "get_weather" in tool_names
    assert "web_search" in tool_names
    assert "play_music" in tool_names
    assert "control_media" in tool_names

    print("\n4. Testing Gemini Tools Schema:")
    gem_tools = svc.get_extension_tools_gemini()
    gem_names = [t["name"] for t in gem_tools]
    print(" -> Gemini tool names:", gem_names)
    assert "get_weather" in gem_names

    print("\n✅ All ExtensionMCPService unit tests PASSED!")

if __name__ == "__main__":
    asyncio.run(run_tests())
