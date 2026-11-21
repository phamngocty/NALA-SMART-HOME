import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

filepath = 'server_nas_hub/app/static/index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

print("Original index.html length:", len(text))

# 1. Add SiliconCloud radio in the providers grid
old_radio_grid = '''                    <label style="background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 12px; cursor: pointer; display: flex; align-items: center; gap: 8px;">
                        <input type="radio" name="aiProviderRadio" value="openrouter" onchange="updateAIProviderUI()">
                        <div>
                            <div style="font-weight: 700; font-size: 13px; color: #c084fc;">OpenRouter (9 Router)</div>
                            <div style="font-size: 11px; color: #94a3b8;">Tự do chọn Claude, Llama, Qwen...</div>
                        </div>
                    </label>'''

new_radio_grid = '''                    <label style="background: #1e293b; border: 1px solid #38bdf8; border-radius: 10px; padding: 12px; cursor: pointer; display: flex; align-items: center; gap: 8px;">
                        <input type="radio" name="aiProviderRadio" value="siliconflow" onchange="updateAIProviderUI()">
                        <div>
                            <div style="font-weight: 700; font-size: 13px; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                                <span>⚡ SiliconCloud</span>
                                <span style="font-size: 10px; background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 1px 6px; border-radius: 4px; font-weight: 700;">XiaoZhi Free</span>
                            </div>
                            <div style="font-size: 11px; color: #94a3b8;">Qwen 2.5 &amp; DeepSeek Miễn Phí</div>
                        </div>
                    </label>
                    <label style="background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 12px; cursor: pointer; display: flex; align-items: center; gap: 8px;">
                        <input type="radio" name="aiProviderRadio" value="openrouter" onchange="updateAIProviderUI()">
                        <div>
                            <div style="font-weight: 700; font-size: 13px; color: #c084fc;">OpenRouter (9 Router)</div>
                            <div style="font-size: 11px; color: #94a3b8;">Tự do chọn Claude, Llama, Qwen Free...</div>
                        </div>
                    </label>'''

assert old_radio_grid in text, "Could not find old_radio_grid in index.html"
text = text.replace(old_radio_grid, new_radio_grid, 1)

# 2. Add SiliconCloud card right after OpenRouter card
old_card_anchor = '''                    <div style="font-size: 11px; color: #64748b;">
                        * Gợi ý model miễn phí / tốc độ cao: <code>google/gemini-2.0-flash-exp:free</code>, <code>deepseek/deepseek-chat</code>, <code>meta-llama/llama-3.3-70b-instruct</code>
                    </div>
                    <div id="testRes_openrouter" style="font-size: 11px; margin-top: 6px;"></div>
                </div>'''

siliconcloud_card = '''                    <div style="font-size: 11px; color: #64748b;">
                        * Gợi ý model miễn phí: <code>qwen/qwen-2.5-72b-instruct:free</code>, <code>deepseek/deepseek-r1:free</code>, <code>google/gemini-2.0-flash-exp:free</code>
                    </div>
                    <div id="testRes_openrouter" style="font-size: 11px; margin-top: 6px;"></div>
                </div>

                <!-- 5. SILICONCLOUD (SILICONFLOW - XIAOZHI OFFICIAL BACKEND) -->
                <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #38bdf8; border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.15);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">
                        <div style="font-weight: 700; font-size: 13px; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                            <span>⚡ SiliconCloud (SiliconFlow - Máy Chủ AI Chuẩn XiaoZhi)</span>
                            <span style="font-size: 10px; background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-weight: 700;">XiaoZhi Backend</span>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <button type="button" class="btn-cancel" onclick="testAIConn('siliconflow')" style="padding: 4px 10px; font-size: 11px; color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); cursor: pointer; border-radius: 6px; background: rgba(56, 189, 248, 0.1);">
                                🧪 Test Kết Nối
                            </button>
                            <a href="https://cloud.siliconflow.cn/account/ak" target="_blank" style="color: #38bdf8; font-size: 11px; text-decoration: underline; display: flex; align-items: center;">
                                Lấy Key Miễn Phí (sk-...) ↗
                            </a>
                        </div>
                    </div>
                    <div style="font-size: 11px; color: #94a3b8; margin-bottom: 12px; line-height: 1.5;">
                        Đây là dịch vụ mà <strong>XiaoZhi (xiaozhi-esp32)</strong> dùng để chạy miễn phí các mô hình <code>Qwen 2.5</code> và <code>DeepSeek R1/V3</code>. Cung cấp miễn phí 100% các model 7B/GLM-4 cùng các model lớn 72B/V3 với tốc độ phản xạ cực nhanh.
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 10px;">
                        <div>
                            <label style="font-size: 11px; color: #cbd5e1; font-weight: 600; display: block; margin-bottom: 4px;">SiliconCloud API Key (sk-...):</label>
                            <input type="password" id="cfgSiliconflowKey" placeholder="sk-..." style="width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #334155; color: white; padding: 8px 10px; border-radius: 6px; font-size: 12px;">
                        </div>
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <label style="font-size: 11px; color: #cbd5e1; font-weight: 600;">Mô hình (Model):</label>
                                <button type="button" onclick="fetchModelsForProvider('siliconflow')" style="background: none; border: none; color: #38bdf8; font-size: 11px; cursor: pointer; text-decoration: underline; padding: 0;">
                                    🔍 Quét API Model
                                </button>
                            </div>
                            <select id="cfgSiliconflowModel" style="width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #334155; color: white; padding: 8px 10px; border-radius: 6px; font-size: 12px;">
                                <option value="Qwen/Qwen2.5-7B-Instruct">Qwen/Qwen2.5-7B-Instruct [Miễn phí 100% · Siêu tốc]</option>
                                <option value="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B">deepseek-ai/DeepSeek-R1-Distill-Qwen-7B [Miễn phí 100% · Suy luận R1]</option>
                                <option value="Qwen/Qwen2.5-Coder-7B-Instruct">Qwen/Qwen2.5-Coder-7B-Instruct [Miễn phí 100% · Coder]</option>
                                <option value="THUDM/glm-4-9b-chat">THUDM/glm-4-9b-chat [Miễn phí 100% · GLM-4]</option>
                                <option value="internlm/internlm2_5-7b-chat">internlm/internlm2_5-7b-chat [Miễn phí 100%]</option>
                                <option value="Qwen/Qwen2.5-32B-Instruct">Qwen/Qwen2.5-32B-Instruct (Qwen 32B Cân bằng cao cấp)</option>
                                <option value="Qwen/Qwen2.5-72B-Instruct">Qwen/Qwen2.5-72B-Instruct (Qwen 72B Đỉnh cao ngôn ngữ)</option>
                                <option value="deepseek-ai/DeepSeek-V3">deepseek-ai/DeepSeek-V3 (DeepSeek V3 Đàm thoại xuất sắc)</option>
                                <option value="deepseek-ai/DeepSeek-R1">deepseek-ai/DeepSeek-R1 (DeepSeek R1 Suy luận sâu)</option>
                                <option value="deepseek-ai/DeepSeek-R1-Distill-Llama-70B">deepseek-ai/DeepSeek-R1-Distill-Llama-70B (R1 Llama 70B)</option>
                            </select>
                        </div>
                    </div>
                    <div id="testRes_siliconflow" style="font-size: 11px; margin-top: 6px;"></div>
                </div>'''

assert old_card_anchor in text, "Could not find old_card_anchor in index.html"
text = text.replace(old_card_anchor, siliconcloud_card, 1)

# 3. Update updateAIProviderUI()
old_names_map = """    const names = {
        'gemini': 'Gemini (Chính)',
        'groq': 'Groq (Chính)',
        'deepseek': 'DeepSeek (Chính)',
        'openrouter': 'OpenRouter (Chính)'
    };
    const order = [prov];
    for (const p of ['groq', 'deepseek', 'gemini', 'openrouter']) {
        if (!order.includes(p)) order.push(p);
    }"""

new_names_map = """    const names = {
        'gemini': 'Gemini (Chính)',
        'siliconflow': 'SiliconCloud (Chính)',
        'groq': 'Groq (Chính)',
        'deepseek': 'DeepSeek (Chính)',
        'openrouter': 'OpenRouter (Chính)'
    };
    const order = [prov];
    for (const p of ['siliconflow', 'groq', 'deepseek', 'gemini', 'openrouter']) {
        if (!order.includes(p)) order.push(p);
    }"""

assert old_names_map in text, "Could not find old_names_map in updateAIProviderUI"
text = text.replace(old_names_map, new_names_map, 1)

# 4. Update testAIConn(provider)
old_test_conn_branch = """    } else if (provider === 'openrouter') {
        apiKey = document.getElementById('cfgOpenrouterKey').value.trim();
        model = document.getElementById('cfgOpenrouterModel').value;
    }"""

new_test_conn_branch = """    } else if (provider === 'openrouter') {
        apiKey = document.getElementById('cfgOpenrouterKey').value.trim();
        model = document.getElementById('cfgOpenrouterModel').value;
    } else if (provider === 'siliconflow') {
        apiKey = document.getElementById('cfgSiliconflowKey')?.value.trim() || '';
        model = document.getElementById('cfgSiliconflowModel')?.value || 'Qwen/Qwen2.5-7B-Instruct';
    }"""

assert old_test_conn_branch in text, "Could not find old_test_conn_branch in testAIConn"
text = text.replace(old_test_conn_branch, new_test_conn_branch, 1)

# 5. Update fetchModelsForProvider(provider)
old_fetch_models_branch = """    } else if (provider === 'openrouter') {
        apiKey = document.getElementById('cfgOpenrouterKey').value.trim();
        selectEl = document.getElementById('cfgOpenrouterModel');
    }"""

new_fetch_models_branch = """    } else if (provider === 'openrouter') {
        apiKey = document.getElementById('cfgOpenrouterKey').value.trim();
        selectEl = document.getElementById('cfgOpenrouterModel');
    } else if (provider === 'siliconflow') {
        apiKey = document.getElementById('cfgSiliconflowKey')?.value.trim() || '';
        selectEl = document.getElementById('cfgSiliconflowModel');
    }"""

assert old_fetch_models_branch in text, "Could not find old_fetch_models_branch in fetchModelsForProvider"
text = text.replace(old_fetch_models_branch, new_fetch_models_branch, 1)

# 6. Update saveAIConfig()
old_save_payload = """        openrouter: {
            api_key: document.getElementById('cfgOpenrouterKey').value.trim(),
            model: document.getElementById('cfgOpenrouterModel').value
        },"""

new_save_payload = """        openrouter: {
            api_key: document.getElementById('cfgOpenrouterKey').value.trim(),
            model: document.getElementById('cfgOpenrouterModel').value
        },
        siliconflow: {
            api_key: document.getElementById('cfgSiliconflowKey')?.value.trim() || '',
            model: document.getElementById('cfgSiliconflowModel')?.value || 'Qwen/Qwen2.5-7B-Instruct',
            base_url: 'https://api.siliconflow.cn/v1'
        },"""

assert old_save_payload in text, "Could not find old_save_payload in saveAIConfig"
text = text.replace(old_save_payload, new_save_payload, 1)

# 7. Update openAIConfigModal() / loadAIConfigData()
old_load_openrouter = """            const orKeyInput = document.getElementById('cfgOpenrouterKey');
            orKeyInput.value = '';
            orKeyInput.placeholder = aiCurrentConfig.openrouter?.has_key ? `Đã lưu key (${aiCurrentConfig.openrouter.api_key_masked}) - Để trống nếu giữ nguyên` : 'Nhập OpenRouter API Key...';
            document.getElementById('cfgOpenrouterModel').value = aiCurrentConfig.openrouter?.model || 'google/gemini-2.0-flash-exp:free';"""

new_load_openrouter = """            const orKeyInput = document.getElementById('cfgOpenrouterKey');
            if (orKeyInput) {
                orKeyInput.value = '';
                orKeyInput.placeholder = aiCurrentConfig.openrouter?.has_key ? `Đã lưu key (${aiCurrentConfig.openrouter.api_key_masked}) - Để trống nếu giữ nguyên` : 'Nhập OpenRouter API Key...';
                document.getElementById('cfgOpenrouterModel').value = aiCurrentConfig.openrouter?.model || 'qwen/qwen-2.5-72b-instruct:free';
            }

            const sfKeyInput = document.getElementById('cfgSiliconflowKey');
            if (sfKeyInput && aiCurrentConfig.siliconflow) {
                sfKeyInput.value = '';
                sfKeyInput.placeholder = aiCurrentConfig.siliconflow.has_key ? `Đã lưu key (${aiCurrentConfig.siliconflow.api_key_masked}) - Để trống nếu giữ nguyên` : 'Nhập SiliconCloud API Key (sk-...)...';
            }
            const sfModelEl = document.getElementById('cfgSiliconflowModel');
            if (sfModelEl && aiCurrentConfig.siliconflow?.model) {
                sfModelEl.value = aiCurrentConfig.siliconflow.model;
            }"""

assert old_load_openrouter in text, "Could not find old_load_openrouter in openAIConfigModal"
text = text.replace(old_load_openrouter, new_load_openrouter, 1)

# Also update loadAIConfigData() loop
code_loop_old = "['gemini', 'groq', 'deepseek', 'openrouter'].forEach(p => {"
code_loop_new = "['gemini', 'groq', 'deepseek', 'openrouter', 'siliconflow'].forEach(p => {"
text = text.replace(code_loop_old, code_loop_new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("✅ Successfully updated index.html with SiliconCloud (Qwen 2.5 & DeepSeek Free Tier) UI!")
