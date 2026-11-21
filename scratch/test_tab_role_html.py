import re

sys_tab_buttons = '''            <!-- Tab Headers -->
            <div class="wizard-tabs" style="border-bottom: 1px solid #334155; margin-bottom: 0; background: #0f172a; padding: 0 20px; display: flex; flex-wrap: wrap;">
                <div class="wizard-tab active" id="tab_sys_role_btn" onclick="switchSystemSettingsTab('role')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🎭 Vai Trò &amp; Giọng Nói (XiaoZhi)
                </div>
                <div class="wizard-tab" id="tab_sys_ai_btn" onclick="switchSystemSettingsTab('ai')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🤖 Mô Hình AI &amp; API Key
                </div>
                <div class="wizard-tab" id="tab_sys_ha_btn" onclick="switchSystemSettingsTab('ha')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    ⚙️ Home Assistant (Pi 5)
                </div>
                <div class="wizard-tab" id="tab_sys_ota_btn" onclick="switchSystemSettingsTab('ota')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🚀 Cập Nhật OTA Firmware
                </div>
            </div>'''

tab_role_html = '''<div id="tab_sys_role" style="display: block; padding: 24px; background: #0b1120;">
    <!-- XiaoZhi Voice Role Box -->
    <div style="background: #182234; border: 1px solid #334155; border-radius: 14px; padding: 22px; margin-bottom: 20px; box-shadow: 0 8px 30px rgba(0,0,0,0.35);">
        
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 12px;">
            <div>
                <h4 style="margin: 0; font-size: 15px; color: #f8fafc; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                    <span>Vai trò giọng nói</span>
                    <span style="font-size: 12px; color: #94a3b8; font-weight: 400;">(Chế độ cá nhân hóa XiaoZhi)</span>
                </h4>
            </div>
            <span style="font-size: 11px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 4px 10px; border-radius: 6px; font-weight: 700; border: 1px solid rgba(56, 189, 248, 0.3);">
                XiaoZhi Standard
            </span>
        </div>

        <!-- Voice Selector Row -->
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
        </div>

        <!-- Cài đặt giọng nói (Collapsible Header & 3 Sliders) -->
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; padding: 16px 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; cursor: pointer;" onclick="toggleVoiceSettingsPanel()">
                <div style="font-size: 14px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
                    <span>Cài đặt giọng nói</span>
                </div>
                <span id="xzSettingsArrow" style="color: #94a3b8; font-size: 12px;">▲</span>
            </div>

            <!-- 3 Sliders Grid -->
            <div id="xzSlidersContainer" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 24px;">
                <!-- Slider 1: Tốc độ nhận dạng -->
                <div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 8px;">
                        <span>Tốc độ nhận dạng</span>
                        <span id="xzVadLabel" style="color: #38bdf8;">Chuẩn</span>
                    </div>
                    <input type="range" id="xzVadSpeed" min="1" max="3" step="1" value="2" oninput="updateVoiceSlidersUI()" style="width: 100%; cursor: pointer; accent-color: #38bdf8;">
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748b; margin-top: 6px;">
                        <span>Chậm</span>
                        <span>Chuẩn</span>
                        <span>Nhanh</span>
                    </div>
                </div>

                <!-- Slider 2: Tốc độ trả lời -->
                <div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 8px;">
                        <span>Tốc độ trả lời</span>
                        <span id="xzRateLabel" style="color: #38bdf8;">Chuẩn</span>
                    </div>
                    <input type="range" id="xzSpeakingRate" min="1" max="3" step="1" value="2" oninput="updateVoiceSlidersUI()" style="width: 100%; cursor: pointer; accent-color: #38bdf8;">
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748b; margin-top: 6px;">
                        <span>Chậm</span>
                        <span>Chuẩn</span>
                        <span>Nhanh</span>
                    </div>
                </div>

                <!-- Slider 3: Cao độ trả lời -->
                <div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 8px;">
                        <span>Cao độ trả lời</span>
                        <span id="xzPitchLabel" style="color: #38bdf8;">Chuẩn</span>
                    </div>
                    <input type="range" id="xzSpeakingPitch" min="1" max="3" step="1" value="2" oninput="updateVoiceSlidersUI()" style="width: 100%; cursor: pointer; accent-color: #38bdf8;">
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748b; margin-top: 6px;">
                        <span>Thấp</span>
                        <span>Chuẩn</span>
                        <span>Cao</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Action Bar -->
        <div style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 22px;">
            <button type="button" onclick="saveXiaoZhiVoiceRole()" style="background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 11px 26px; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.35); transition: opacity 0.2s;">
                💾 Lưu Vai Trò &amp; Cài Đặt Giọng Nói
            </button>
        </div>
    </div>
</div>'''

print("tab_role_html length:", len(tab_role_html))
