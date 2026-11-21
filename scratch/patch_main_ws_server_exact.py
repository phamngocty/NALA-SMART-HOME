with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    code = f.read()

idx = code.find('async def get_ai_models(')
assert idx != -1, "get_ai_models not found"
end_marker = 'return JSONResponse({"status": "success", "provider": req.provider, "models": models})'
idx_end = code.find(end_marker, idx)
assert idx_end != -1, "end_marker not found"

idx_insert = idx_end + len(end_marker)

extension_endpoints = """

class WeatherTestRequest(BaseModel):
    location: Optional[str] = "Hà Nội"

@app.post("/api/extensions/test_weather")
async def test_weather_endpoint(req: WeatherTestRequest):
    \"\"\"Test trực tiếp dịch vụ thời tiết Open-Meteo.\"\"\"
    loc = (req.location or "Hà Nội").strip()
    if hasattr(ai_router, "extension_service"):
        res = await ai_router.extension_service.get_weather(loc)
        return JSONResponse({"status": "success", "result": res})
    return JSONResponse({"status": "error", "message": "Extension service chưa khởi tạo"}, status_code=500)

class SearchTestRequest(BaseModel):
    query: str

@app.post("/api/extensions/test_search")
async def test_search_endpoint(req: SearchTestRequest):
    \"\"\"Test trực tiếp tìm kiếm DuckDuckGo / Wikipedia.\"\"\"
    q = (req.query or "").strip()
    if hasattr(ai_router, "extension_service"):
        res = await ai_router.extension_service.web_search(q)
        return JSONResponse({"status": "success", "result": res})
    return JSONResponse({"status": "error", "message": "Extension service chưa khởi tạo"}, status_code=500)

class MCPTestRequest(BaseModel):
    endpoint_url: str

@app.post("/api/extensions/test_mcp")
async def test_mcp_endpoint(req: MCPTestRequest):
    \"\"\"Test kết nối và quét tools từ MCP Server endpoint.\"\"\"
    url = (req.endpoint_url or "").strip()
    if hasattr(ai_router, "extension_service"):
        res = await ai_router.extension_service.test_mcp_server(url)
        return JSONResponse(res)
    return JSONResponse({"status": "error", "message": "Extension service chưa khởi tạo"}, status_code=500)

@app.get("/api/extensions/media_players")
async def get_media_players():
    \"\"\"Lấy danh sách các loa / Media Player từ Home Assistant.\"\"\"
    players = []
    if ha_bridge and hasattr(ha_bridge, "entities") and ha_bridge.entities:
        for eid, data in ha_bridge.entities.items():
            if eid.startswith("media_player."):
                f_name = data.get("attributes", {}).get("friendly_name", eid)
                state = data.get("state", "idle")
                players.append({"entity_id": eid, "friendly_name": f_name, "state": state})
    return JSONResponse({"status": "success", "players": players})"""

code = code[:idx_insert] + extension_endpoints + code[idx_insert:]

with open('server_nas_hub/app/main_ws_server.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("✅ Successfully added extension endpoints to server_nas_hub/app/main_ws_server.py!")
