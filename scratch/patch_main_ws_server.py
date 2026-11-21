with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    code = f.read()

target = """@app.post("/api/ai/models")
async def get_ai_models(req: AIModelsRequest):
    \"\"\"Lấy danh sách các model khả dụng trực tiếp từ API của từng hãng.\"\"\"
    models = await ai_router.list_available_models(req.provider, req.api_key, req.base_url)
    return JSONResponse({"status": "success", "models": models})"""

extension_endpoints = """@app.post("/api/ai/models")
async def get_ai_models(req: AIModelsRequest):
    \"\"\"Lấy danh sách các model khả dụng trực tiếp từ API của từng hãng.\"\"\"
    models = await ai_router.list_available_models(req.provider, req.api_key, req.base_url)
    return JSONResponse({"status": "success", "models": models})

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

assert target in code, "target not found in main_ws_server.py"
code = code.replace(target, extension_endpoints, 1)

with open('server_nas_hub/app/main_ws_server.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("✅ Successfully added extension endpoints to server_nas_hub/app/main_ws_server.py!")
