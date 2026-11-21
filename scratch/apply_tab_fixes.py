with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix tab_vp_test
old_test = '''                <!-- TAB 4: TEST IDENTIFICATION -->
                <div id="tab_upm_test" style="display: none;">
                    <div id="tab_vp_test" style="display: none;">'''

new_test = '''                <!-- TAB 4: TEST IDENTIFICATION -->
                <div id="tab_upm_test" style="display: none;">
                    <div id="tab_vp_test" style="display: block;">'''

assert old_test in content, "old_test target not found!"
content = content.replace(old_test, new_test, 1)
print("✅ Fix 1 (tab_vp_test) applied.")

# 2. Fix updateActiveIntercomCallsBanner
old_intercom = "if (typeof updateActiveIntercomCallsBanner === 'function') updateActiveIntercomCallsBanner();"
new_intercom = "if (typeof updateActiveIntercomCallsUI === 'function') updateActiveIntercomCallsUI();"

assert old_intercom in content, "old_intercom target not found!"
content = content.replace(old_intercom, new_intercom, 1)
print("✅ Fix 2 (updateActiveIntercomCallsUI) applied.")

# 3. Update tab_sys_role layout
old_role_block = '''        <!-- Voice Selector Row -->
        <div style="display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; position: relative;">
            <!-- Language Dropdown -->
            <div style="min-width: 140px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; font-size: 13px; font-weight: 700; color: #f8fafc; cursor: pointer;">
                <span style="display: flex; align-items: center; gap: 8px;">
                    <span style="color: #38bdf8; font-weight: 800;">文A</span>
                    <span>Tiếng Việt</span>
                </span>
                <span style="color: #64748b; font-size: 11px;">▼</span>
            </div>

            <!-- Custom Voice Dropdown Picker -->
            <div style="flex: 1; min-width: 300px; position: relative;" id="xzVoiceDropdownContainer">
                <div id="xzVoiceTrigger" onclick="toggleVoiceDropdown(event)" style="display: flex; justify-content: space-between; align-items: center; background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 10px 14px; cursor: pointer; color: #f8fafc; font-weight: 600; font-size: 14px; transition: border-color 0.2s;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span id="xzVoiceSelectedCheck" style="color: #38bdf8; font-weight: bold;">✓</span>
                        <span id="xzSelectedVoiceName">Giọng nữ (Female Voice)</span>
                    </div>
                    <span id="xzDropdownArrow" style="font-size: 11px; color: #94a3b8; transition: transform 0.2s;">▲</span>
                </div>

                <!-- Open Dropdown Menu -->
                <div id="xzVoiceMenu" style="display: none; position: absolute; top: calc(100% + 6px); left: 0; right: 0; background: #0f172a; border: 1px solid #334155; border-radius: 10px; box-shadow: 0 16px 36px rgba(0,0,0,0.65); z-index: 1000; overflow: hidden;">
                    <!-- Search Input inside Dropdown -->
                    <div style="padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); display: flex; align-items: center; gap: 8px; background: #182234;">
                        <span style="color: #64748b; font-size: 13px;">🔍</span>
                        <input type="text" id="xzVoiceSearchInput" oninput="filterVoiceList(this.value)" placeholder="Tìm giọng nói" style="background: transparent; border: none; outline: none; color: #fff; font-size: 13px; width: 100%;">
                    </div>

                    <!-- Voice Items List -->
                    <div id="xzVoiceList" style="max-height: 250px; overflow-y: auto;">
                        <!-- Injected via JavaScript -->
                    </div>
                </div>
            </div>
        </div>

        <!-- Giới thiệu vai trò (Role Persona) -->
        <div style="margin-bottom: 22px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <label style="font-size: 13px; font-weight: 700; color: #38bdf8; margin: 0; display: flex; align-items: center; gap: 6px;">
                    <span>Giới thiệu vai trò</span>
                </label>
                <span style="font-size: 11px; color: #64748b;">(Tự động điều chỉnh phong cách đàm thoại của Nala)</span>
            </div>
            <textarea id="xzRolePersona" rows="6" style="width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 14px 16px; border-radius: 10px; font-size: 13px; line-height: 1.6; font-family: inherit; resize: vertical;" placeholder="Xin chào! Mình là Nala, trợ lý ảo thông minh của gia đình bạn..."></textarea>
        </div>'''

new_role_block = '''        <!-- 2-Column Split: Giới thiệu vai trò (Left) & Bộ chọn giọng nói (Right) chuẩn XiaoZhi Console -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 22px; align-items: start;">
            <!-- Left Column: Giới thiệu vai trò -->
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <label style="font-size: 13px; font-weight: 700; color: #38bdf8; margin: 0; display: flex; align-items: center; gap: 6px;">
                        <span>Giới thiệu vai trò</span>
                    </label>
                    <span style="font-size: 11px; color: #64748b;">(Tính cách &amp; phong cách xưng hô)</span>
                </div>
                <textarea id="xzRolePersona" rows="7" style="width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 14px 16px; border-radius: 10px; font-size: 13px; line-height: 1.6; font-family: inherit; resize: vertical; min-height: 160px;" placeholder="Xin chào! Mình là Nala, trợ lý ảo thông minh của gia đình bạn..."></textarea>
            </div>

            <!-- Right Column: Ngôn ngữ & Bộ chọn giọng nói XiaoZhi -->
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <label style="font-size: 13px; font-weight: 700; color: #f8fafc; margin: 0;">
                        <span>Giọng nói mẫu</span>
                    </label>
                    <span style="font-size: 11px; color: #94a3b8;">(Bấm ▷ để nghe thử trực tiếp)</span>
                </div>

                <div style="display: flex; gap: 10px; margin-bottom: 12px; position: relative;">
                    <!-- Language Dropdown -->
                    <div style="width: 130px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; font-size: 13px; font-weight: 700; color: #f8fafc; cursor: pointer;">
                        <span style="display: flex; align-items: center; gap: 8px;">
                            <span style="color: #38bdf8; font-weight: 800;">文A</span>
                            <span>Tiếng Việt</span>
                        </span>
                        <span style="color: #64748b; font-size: 11px;">▼</span>
                    </div>

                    <!-- Custom Voice Dropdown Picker -->
                    <div style="flex: 1; min-width: 200px; position: relative;" id="xzVoiceDropdownContainer">
                        <div id="xzVoiceTrigger" onclick="toggleVoiceDropdown(event)" style="display: flex; justify-content: space-between; align-items: center; background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 10px 14px; cursor: pointer; color: #f8fafc; font-weight: 600; font-size: 13px; transition: border-color 0.2s;">
                            <div style="display: flex; align-items: center; gap: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                <span id="xzVoiceSelectedCheck" style="color: #38bdf8; font-weight: bold;">✓</span>
                                <span id="xzSelectedVoiceName">Giọng nữ (Female Voice)</span>
                            </div>
                            <span id="xzDropdownArrow" style="font-size: 11px; color: #94a3b8; transition: transform 0.2s;">▲</span>
                        </div>

                        <!-- Open Dropdown Menu -->
                        <div id="xzVoiceMenu" style="display: none; position: absolute; top: calc(100% + 6px); left: 0; right: 0; background: #0f172a; border: 1px solid #334155; border-radius: 10px; box-shadow: 0 16px 36px rgba(0,0,0,0.65); z-index: 1000; overflow: hidden;">
                            <!-- Search Input inside Dropdown -->
                            <div style="padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); display: flex; align-items: center; gap: 8px; background: #182234;">
                                <span style="color: #64748b; font-size: 13px;">🔍</span>
                                <input type="text" id="xzVoiceSearchInput" oninput="filterVoiceList(this.value)" placeholder="Tìm giọng nói" style="background: transparent; border: none; outline: none; color: #fff; font-size: 13px; width: 100%;">
                            </div>

                            <!-- Voice Items List -->
                            <div id="xzVoiceList" style="max-height: 250px; overflow-y: auto;">
                                <!-- Injected via JavaScript -->
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Info note -->
                <div style="font-size: 12px; color: #94a3b8; line-height: 1.5; background: rgba(15, 23, 42, 0.5); padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.04);">
                    💡 <em>Hỗ trợ 6 giọng AI tự nhiên chuẩn Edge-TTS &amp; Google Fast TTS 0.15s phản xạ tức thì.</em>
                </div>
            </div>
        </div>'''

assert old_role_block in content, "old_role_block target not found!"
content = content.replace(old_role_block, new_role_block, 1)
print("✅ Fix 3 (tab_sys_role 2-column layout) applied.")

with open('server_nas_hub/app/static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("🎉 File index.html successfully updated!")
