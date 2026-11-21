with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add tab button for 'ext' in wizard-tabs
tab_btn_target = """                <div class="wizard-tab" id="tab_sys_ai_btn" onclick="switchSystemSettingsTab('ai')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🤖 Mô Hình AI &amp; API Key
                </div>"""

tab_btn_replacement = """                <div class="wizard-tab" id="tab_sys_ai_btn" onclick="switchSystemSettingsTab('ai')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🤖 Mô Hình AI &amp; API Key
                </div>
                <div class="wizard-tab" id="tab_sys_ext_btn" onclick="switchSystemSettingsTab('ext')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🔌 Dịch Vụ Mở Rộng &amp; MCP
                </div>"""

assert tab_btn_target in html, "tab_btn_target not found"
html = html.replace(tab_btn_target, tab_btn_replacement, 1)

# 2. Add tab_sys_ext content pane right before <div id="tab_sys_ha"
idx_target_pane = html.find('<div id="tab_sys_ha"')
assert idx_target_pane != -1, "tab_sys_ha wrapper not found"

ext_html_pane = """
                <!-- TAB EXTENSIONS & MCP (XiaoZhi Step 3) -->
                <div id="tab_sys_ext" style="display: none; padding: 24px; background: #0b1120;">
                    <!-- Header Info -->
                    <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.9)); border: 1px solid #334155; border-radius: 14px; padding: 18px 22px; margin-bottom: 22px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
                        <div>
                            <h4 style="margin: 0; font-size: 16px; color: #f8fafc; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                                <span>🔌 Dịch Vụ Mở Rộng &amp; Điểm Cuối MCP (XiaoZhi Extensions)</span>
                                <span style="font-size: 11px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 3px 8px; border-radius: 6px; border: 1px solid rgba(56, 189, 248, 0.3);">Chuẩn XiaoZhi Console</span>
                            </h4>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 5px;">
                                Cung cấp các công cụ gọi hàm (Tool Calling) thông minh: Thời tiết, Tìm kiếm trực tuyến, Phát nhạc qua loa và kết nối máy chủ MCP tùy biến.
                            </div>
                        </div>
                    </div>

                    <!-- 1. DỊCH VỤ CHÍNH THỨC (OFFICIAL SERVICES) -->
                    <div style="margin-bottom: 24px;">
                        <div style="font-size: 13px; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 14px; display: flex; align-items: center; gap: 8px;">
                            <span>🌟 Dịch Vụ Chính Thức (Official Tools)</span>
                        </div>

                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 18px;">
                            <!-- Card 1: Thời tiết -->
                            <div style="background: #182234; border: 1px solid #334155; border-radius: 12px; padding: 18px; display: flex; flex-direction: column; justify-content: space-between;">
                                <div>
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                        <div style="font-size: 14px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
                                            <span>🌦️ Thời Tiết (Open-Meteo)</span>
                                        </div>
                                        <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 12px; font-weight: 600; color: #34d399;">
                                            <input type="checkbox" id="chkExtWeather" style="accent-color: #10b981; width: 16px; height: 16px;">
                                            <span>Kích hoạt</span>
                                        </label>
                                    </div>
                                    <p style="font-size: 12px; color: #94a3b8; line-height: 1.5; margin: 0 0 12px 0;">
                                        Tra cứu nhiệt độ, độ ẩm, gió và dự báo mưa theo địa điểm thời gian thực (Miễn phí 100%, không cần API key).
                                    </p>
                                    <div style="display: flex; gap: 8px; margin-bottom: 10px;">
                                        <input type="text" id="extWeatherLocation" placeholder="Địa điểm (VD: Hà Nội, Hồ Chí Minh)" value="Hà Nội" style="flex: 1; background: #0f172a; border: 1px solid #334155; color: #fff; padding: 8px 12px; border-radius: 8px; font-size: 12px;">
                                        <button type="button" onclick="testWeatherService()" style="background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; padding: 8px 14px; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer;">
                                            Kiểm tra
                                        </button>
                                    </div>
                                    <div id="extWeatherResult" style="display: none; background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px 12px; font-size: 11px; color: #cbd5e1; line-height: 1.5;"></div>
                                </div>
                            </div>

                            <!-- Card 2: Tìm kiếm trực tuyến -->
                            <div style="background: #182234; border: 1px solid #334155; border-radius: 12px; padding: 18px; display: flex; flex-direction: column; justify-content: space-between;">
                                <div>
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                        <div style="font-size: 14px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
                                            <span>🔍 Tìm Kiếm Web (DuckDuckGo)</span>
                                        </div>
                                        <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 12px; font-weight: 600; color: #34d399;">
                                            <input type="checkbox" id="chkExtSearch" style="accent-color: #10b981; width: 16px; height: 16px;">
                                            <span>Kích hoạt</span>
                                        </label>
                                    </div>
                                    <p style="font-size: 12px; color: #94a3b8; line-height: 1.5; margin: 0 0 12px 0;">
                                        Tìm kiếm dữ liệu thời gian thực, tin tức, giá vàng, tỷ giá và kiến thức bách khoa tiếng Việt.
                                    </p>
                                    <div style="display: flex; gap: 8px; margin-bottom: 10px;">
                                        <input type="text" id="extSearchQuery" placeholder="Từ khóa thử (VD: giá vàng hôm nay, hồ gươm)" value="hồ gươm" style="flex: 1; background: #0f172a; border: 1px solid #334155; color: #fff; padding: 8px 12px; border-radius: 8px; font-size: 12px;">
                                        <button type="button" onclick="testSearchService()" style="background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; padding: 8px 14px; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer;">
                                            Tìm thử
                                        </button>
                                    </div>
                                    <div id="extSearchResult" style="display: none; background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px 12px; font-size: 11px; color: #cbd5e1; line-height: 1.5; max-height: 120px; overflow-y: auto;"></div>
                                </div>
                            </div>

                            <!-- Card 3: Âm nhạc & Đa phương tiện -->
                            <div style="background: #182234; border: 1px solid #334155; border-radius: 12px; padding: 18px; grid-column: 1 / -1;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                    <div style="font-size: 14px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
                                        <span>🎵 Âm Nhạc &amp; Loa Media Player (Home Assistant)</span>
                                    </div>
                                    <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 12px; font-weight: 600; color: #34d399;">
                                        <input type="checkbox" id="chkExtMusic" style="accent-color: #10b981; width: 16px; height: 16px;">
                                        <span>Kích hoạt</span>
                                    </label>
                                </div>
                                <p style="font-size: 12px; color: #94a3b8; line-height: 1.5; margin: 0 0 12px 0;">
                                    Cho phép người dùng ra lệnh bằng giọng nói để mở bài hát, ca sĩ, thể loại nhạc và điều khiển tạm dừng / chuyển bài trên loa Home Assistant.
                                </p>
                                <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
                                    <div style="flex: 1; min-width: 280px;">
                                        <label style="font-size: 11px; font-weight: 700; color: #cbd5e1; margin-bottom: 5px; display: block;">
                                            Loa phát nhạc mặc định (Default Media Player):
                                        </label>
                                        <select id="extMusicPlayer" style="width: 100%; background: #0f172a; border: 1px solid #334155; color: #fff; padding: 9px 12px; border-radius: 8px; font-size: 12px;">
                                            <option value="">-- Tự động chọn theo phòng của micro hoặc loa đang phát --</option>
                                        </select>
                                    </div>
                                    <button type="button" onclick="loadMediaPlayersList()" style="margin-top: 18px; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; padding: 9px 14px; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer;">
                                        🔄 Quét Lại Loa HA
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 2. DỊCH VỤ TÙY CHỈNH (CUSTOM MCP ENDPOINT) -->
                    <div style="background: #182234; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                            <div>
                                <h4 style="margin: 0; font-size: 14px; color: #f8fafc; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                                    <span>⚡ Điểm Cuối MCP (Model Context Protocol)</span>
                                    <span style="font-size: 10px; background: rgba(168, 85, 247, 0.2); color: #c084fc; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(168, 85, 247, 0.3);">Chuẩn Anthropic MCP</span>
                                </h4>
                                <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">
                                    Tích hợp máy chủ MCP bên ngoài (SSE / HTTP JSON-RPC 2.0). NALA sẽ tự động nạp toàn bộ công cụ của MCP Server vào LLM.
                                </div>
                            </div>
                            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 12px; font-weight: 600; color: #34d399;">
                                <input type="checkbox" id="chkExtMcp" style="accent-color: #10b981; width: 16px; height: 16px;">
                                <span>Bật MCP</span>
                            </label>
                        </div>

                        <div style="display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap;">
                            <input type="text" id="extMcpEndpoint" placeholder="URL máy chủ MCP (Ví dụ: http://192.168.1.50:8000/mcp hoặc /sse)" style="flex: 1; min-width: 280px; background: #0f172a; border: 1px solid #334155; color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 13px;">
                            <button type="button" id="btnTestMcp" onclick="testMCPService()" style="background: linear-gradient(135deg, #8b5cf6, #6d28d9); border: none; color: white; padding: 10px 18px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(139, 92, 246, 0.35);">
                                ⚡ Quét &amp; Kiểm Tra MCP Tools
                            </button>
                        </div>

                        <div id="extMcpStatusAlert" style="display: none; padding: 10px 14px; border-radius: 8px; font-size: 12px; margin-bottom: 14px;"></div>

                        <!-- Discovered Tools Container -->
                        <div id="extMcpToolsContainer" style="display: none;">
                            <div style="font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 8px;">
                                📦 Danh Sách Công Cụ Được Phát Hiện Từ Máy Chủ MCP:
                            </div>
                            <div id="extMcpToolsList" style="max-height: 220px; overflow-y: auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;">
                                <!-- Rendered via JS -->
                            </div>
                        </div>
                    </div>

                    <!-- Action Bar -->
                    <div style="display: flex; justify-content: flex-end; gap: 12px;">
                        <button type="button" onclick="saveExtensionConfig()" style="background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 11px 26px; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.35); transition: opacity 0.2s;">
                            💾 Lưu Cấu Hình Mở Rộng &amp; MCP
                        </button>
                    </div>
                </div>
"""

html = html[:idx_target_pane] + ext_html_pane + "\n" + html[idx_target_pane:]

# 3. Update switchSystemSettingsTab JS function
old_switch_tab = """function switchSystemSettingsTab(tabId) {
    const tabs = ['role', 'ai', 'ha', 'ota'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab_sys_${t}_btn`);
        const content = document.getElementById(`tab_sys_${t}`);
        if (btn) btn.classList.toggle('active', t === tabId);
        if (content) content.style.display = (t === tabId) ? 'block' : 'none';
    });
    if (tabId === 'role') loadXiaoZhiVoiceRole();
    if (tabId === 'ai') loadAIConfigData();
    if (tabId === 'ha') loadHAConfigData();
    if (tabId === 'ota') loadOTAData();
}"""

new_switch_tab = """function switchSystemSettingsTab(tabId) {
    const tabs = ['role', 'ai', 'ext', 'ha', 'ota'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab_sys_${t}_btn`);
        const content = document.getElementById(`tab_sys_${t}`);
        if (btn) btn.classList.toggle('active', t === tabId);
        if (content) content.style.display = (t === tabId) ? 'block' : 'none';
    });
    if (tabId === 'role') loadXiaoZhiVoiceRole();
    if (tabId === 'ai') loadAIConfigData();
    if (tabId === 'ext') loadExtensionData();
    if (tabId === 'ha') loadHAConfigData();
    if (tabId === 'ota') loadOTAData();
}"""

assert old_switch_tab in html, "old_switch_tab not found"
html = html.replace(old_switch_tab, new_switch_tab, 1)

# 4. Add Extension JS Functions
extension_js_code = """
// ==========================================
// XIAOZHI EXTENSIONS & MCP CLIENT CONTROLLER
// ==========================================
let currentDiscoveredMcpTools = [];

async function loadExtensionData() {
    try {
        const res = await fetch('/api/ai/config');
        if (!res.ok) return;
        const data = await res.json();
        const ext = data.extensions || {};

        const chkWeather = document.getElementById('chkExtWeather');
        if (chkWeather) chkWeather.checked = (ext.weather_enabled !== false);

        const txtWeatherLoc = document.getElementById('extWeatherLocation');
        if (txtWeatherLoc) txtWeatherLoc.value = ext.weather_location || 'Hà Nội';

        const chkSearch = document.getElementById('chkExtSearch');
        if (chkSearch) chkSearch.checked = (ext.search_enabled !== false);

        const chkMusic = document.getElementById('chkExtMusic');
        if (chkMusic) chkMusic.checked = (ext.music_enabled !== false);

        const chkMcp = document.getElementById('chkExtMcp');
        if (chkMcp) chkMcp.checked = (ext.mcp_enabled === true);

        const txtMcpEndpoint = document.getElementById('extMcpEndpoint');
        if (txtMcpEndpoint) txtMcpEndpoint.value = ext.mcp_endpoint || '';

        await loadMediaPlayersList(ext.music_default_player);
    } catch (e) {
        console.error("loadExtensionData error:", e);
    }
}

async function loadMediaPlayersList(selectedPlayer = "") {
    const selectEl = document.getElementById('extMusicPlayer');
    if (!selectEl) return;

    try {
        const res = await fetch('/api/extensions/media_players');
        if (!res.ok) return;
        const data = await res.json();
        const players = data.players || [];

        let html = '<option value="">-- Tự động chọn theo phòng của micro hoặc loa đang phát --</option>';
        players.forEach(p => {
            const isSel = (p.entity_id === selectedPlayer) ? 'selected' : '';
            html += `<option value="${p.entity_id}" ${isSel}>${p.friendly_name} (${p.entity_id}) [${p.state}]</option>`;
        });
        selectEl.innerHTML = html;
    } catch (e) {
        console.error("loadMediaPlayersList error:", e);
    }
}

async function testWeatherService() {
    const locInput = document.getElementById('extWeatherLocation');
    const resBox = document.getElementById('extWeatherResult');
    if (!locInput || !resBox) return;

    const loc = locInput.value.trim() || 'Hà Nội';
    resBox.style.display = 'block';
    resBox.innerHTML = '<span style="color: #fbbf24;">⏳ Đang tra cứu thời tiết ' + loc + '...</span>';

    try {
        const res = await fetch('/api/extensions/test_weather', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ location: loc })
        });
        const data = await res.json();
        if (data.status === 'success') {
            resBox.innerHTML = '<span style="color: #34d399; font-weight: 600;">🌤️ Kết quả:</span> ' + data.result;
        } else {
            resBox.innerHTML = '<span style="color: #f87171;">❌ Lỗi: ' + (data.message || 'Không thể tra cứu') + '</span>';
        }
    } catch (e) {
        resBox.innerHTML = '<span style="color: #f87171;">❌ Lỗi kết nối: ' + e.message + '</span>';
    }
}

async function testSearchService() {
    const queryInput = document.getElementById('extSearchQuery');
    const resBox = document.getElementById('extSearchResult');
    if (!queryInput || !resBox) return;

    const q = queryInput.value.trim();
    if (!q) {
        alert('Vui lòng nhập từ khóa tìm kiếm');
        return;
    }

    resBox.style.display = 'block';
    resBox.innerHTML = '<span style="color: #fbbf24;">⏳ Đang tìm kiếm trực tuyến về "' + q + '"...</span>';

    try {
        const res = await fetch('/api/extensions/test_search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: q })
        });
        const data = await res.json();
        if (data.status === 'success') {
            resBox.innerHTML = '<span style="color: #34d399; font-weight: 600;">🔎 Kết quả:</span> ' + data.result;
        } else {
            resBox.innerHTML = '<span style="color: #f87171;">❌ Lỗi: ' + (data.message || 'Không có kết quả') + '</span>';
        }
    } catch (e) {
        resBox.innerHTML = '<span style="color: #f87171;">❌ Lỗi kết nối: ' + e.message + '</span>';
    }
}

async function testMCPService() {
    const endpointInput = document.getElementById('extMcpEndpoint');
    const alertBox = document.getElementById('extMcpStatusAlert');
    const toolsContainer = document.getElementById('extMcpToolsContainer');
    const toolsList = document.getElementById('extMcpToolsList');
    const btn = document.getElementById('btnTestMcp');

    if (!endpointInput || !alertBox) return;
    const url = endpointInput.value.trim();
    if (!url) {
        alert('Vui lòng nhập URL máy chủ MCP');
        return;
    }

    if (btn) btn.innerHTML = '⏳ Đang kết nối...';
    alertBox.style.display = 'block';
    alertBox.style.background = 'rgba(251, 191, 36, 0.15)';
    alertBox.style.border = '1px solid rgba(251, 191, 36, 0.3)';
    alertBox.style.color = '#fbbf24';
    alertBox.innerHTML = '⏳ Đang gửi yêu cầu JSON-RPC "tools/list" đến ' + url + '...';

    try {
        const res = await fetch('/api/extensions/test_mcp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ endpoint_url: url })
        });
        const data = await res.json();
        if (btn) btn.innerHTML = '⚡ Quét &amp; Kiểm Tra MCP Tools';

        if (data.status === 'success') {
            alertBox.style.background = 'rgba(16, 185, 129, 0.15)';
            alertBox.style.border = '1px solid rgba(16, 185, 129, 0.3)';
            alertBox.style.color = '#34d399';
            alertBox.innerHTML = '✅ ' + data.message;

            const tools = data.tools || [];
            currentDiscoveredMcpTools = tools;

            if (tools.length > 0 && toolsContainer && toolsList) {
                toolsContainer.style.display = 'block';
                let html = '';
                tools.forEach(t => {
                    html += '<div style="padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); font-size: 12px;">'
                         + '<div style="font-weight: 700; color: #c084fc; display: flex; align-items: center; gap: 6px;">'
                         + '<span>🔧 ' + t.name + '</span>'
                         + '</div>'
                         + '<div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">' + (t.description || 'Không có mô tả') + '</div>'
                         + '</div>';
                });
                toolsList.innerHTML = html;
            }
        } else {
            alertBox.style.background = 'rgba(239, 68, 68, 0.15)';
            alertBox.style.border = '1px solid rgba(239, 68, 68, 0.3)';
            alertBox.style.color = '#f87171';
            alertBox.innerHTML = '❌ ' + (data.message || 'Không thể kết nối MCP Server');
            if (toolsContainer) toolsContainer.style.display = 'none';
        }
    } catch (e) {
        if (btn) btn.innerHTML = '⚡ Quét &amp; Kiểm Tra MCP Tools';
        alertBox.style.background = 'rgba(239, 68, 68, 0.15)';
        alertBox.style.border = '1px solid rgba(239, 68, 68, 0.3)';
        alertBox.style.color = '#f87171';
        alertBox.innerHTML = '❌ Lỗi kết nối: ' + e.message;
    }
}

async function saveExtensionConfig() {
    const chkWeather = document.getElementById('chkExtWeather');
    const txtWeatherLoc = document.getElementById('extWeatherLocation');
    const chkSearch = document.getElementById('chkExtSearch');
    const chkMusic = document.getElementById('chkExtMusic');
    const selMusicPlayer = document.getElementById('extMusicPlayer');
    const chkMcp = document.getElementById('chkExtMcp');
    const txtMcpEndpoint = document.getElementById('extMcpEndpoint');

    const extPayload = {
        weather_enabled: chkWeather ? chkWeather.checked : true,
        weather_location: txtWeatherLoc ? txtWeatherLoc.value.trim() : 'Hà Nội',
        search_enabled: chkSearch ? chkSearch.checked : true,
        music_enabled: chkMusic ? chkMusic.checked : true,
        music_default_player: selMusicPlayer ? selMusicPlayer.value : '',
        mcp_enabled: chkMcp ? chkMcp.checked : false,
        mcp_endpoint: txtMcpEndpoint ? txtMcpEndpoint.value.trim() : ''
    };

    try {
        const curRes = await fetch('/api/ai/config');
        const curConfig = curRes.ok ? await curRes.json() : {};

        const payload = Object.assign({}, curConfig, {
            extensions: extPayload
        });

        const res = await fetch('/api/ai/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.status === 'success') {
            alert('✅ Đã lưu cấu hình Dịch Vụ Mở Rộng & MCP thành công!');
        } else {
            alert('❌ Lỗi: ' + (data.message || 'Không thể lưu cấu hình'));
        }
    } catch (e) {
        alert('Lỗi kết nối: ' + e.message);
    }
}
"""

idx_close_script = html.rfind('</script>')
assert idx_close_script != -1, "closing script tag not found"
html = html[:idx_close_script] + "\n" + extension_js_code + "\n" + html[idx_close_script:]

with open('server_nas_hub/app/static/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Successfully injected Tab Extensions & MCP UI and JavaScript into index.html!")
