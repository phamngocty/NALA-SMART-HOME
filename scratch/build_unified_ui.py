import re
import sys
import shutil

sys.stdout.reconfigure(encoding='utf-8')

SRC = 'server_nas_hub/app/static/index.html'
BAK = 'server_nas_hub/app/static/index.html.bak_v306'

# 1. Backup original file
shutil.copyfile(SRC, BAK)
print(f"Created backup: {BAK}")

with open(SRC, 'r', encoding='utf-8') as f:
    content = f.read()

# 2. Update TARGET_VER to v3.1.0
content = content.replace('var TARGET_VER = "v3.0.6";', 'var TARGET_VER = "v3.1.0";')
content = content.replace('var TARGET_VER = "v3.0.5";', 'var TARGET_VER = "v3.1.0";')

# 3. Update Header Buttons (Remove duplicate All-House Config and use 4 Unified Center Buttons)
old_header_buttons_pattern = r'<div class="badge-pill"[^>]*onclick="syncSystemTime\(\)"[^>]*>.*?</div>\s*<button class="btn-allhouse-header".*?<button class="btn-memory-header"[^>]*>.*?</button>'

new_header_buttons = '''<div class="badge-pill" style="cursor: pointer; background: rgba(56, 189, 248, 0.1); border-color: rgba(56, 189, 248, 0.35);" onclick="syncSystemTime()" title="Bấm để đồng bộ giờ thực GMT+7 xuống toàn bộ màn hình ESP32">
                    <span style="font-size: 13px;">🕒</span>
                    <span id="headerClockText" style="color: #38bdf8; font-weight: 700;">--:--:--</span>
                    <span style="font-size: 10px; background: #0284c7; color: white; padding: 1px 6px; border-radius: 4px; font-weight: 700;">Đồng Bộ Giờ</span>
                </div>

                <!-- 1. HỒ SƠ & TRÍ NHỚ (Gộp Vân Giọng & Trí Nhớ Nala) -->
                <button type="button" class="btn-hub-nav" onclick="openUserProfileMemoryModal()" style="background: linear-gradient(135deg, #06b6d4, #0284c7); border: none; color: white; padding: 7px 15px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(6, 182, 212, 0.35); transition: all 0.2s;">
                    👤 Hồ Sơ &amp; Trí Nhớ
                </button>

                <!-- 2. TỰ ĐỘNG HÓA NGỮ CẢNH (FSM Radar/Lux & Rule Engine) -->
                <button type="button" class="btn-hub-nav" onclick="openLivingContextAutomationModal()" style="background: linear-gradient(135deg, #10b981, #059669); border: none; color: white; padding: 7px 15px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35); transition: all 0.2s;">
                    🌙 Tự Động Hóa Ngữ Cảnh
                </button>

                <!-- 3. GIAO TIẾP & LỊCH SỬ (Intercom & Voice History) -->
                <button type="button" class="btn-hub-nav" onclick="openCommunicationModal()" style="background: linear-gradient(135deg, #f59e0b, #d97706); border: none; color: white; padding: 7px 15px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.35); transition: all 0.2s;">
                    🎙️ Giao Tiếp &amp; Lịch Sử
                </button>

                <!-- LIVE CALL INDICATOR -->
                <span id="headerActiveCallPill" style="display: none; background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: #fca5a5; font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 8px; cursor: pointer; align-items: center; gap: 6px; animation: pulse 1.5s infinite;" onclick="openCommunicationModal('intercom')">
                    <span style="display: inline-block; width: 8px; height: 8px; background: #ef4444; border-radius: 50%;"></span>
                    <span id="headerActiveCallText">Đàm Thoại Rảnh Tay</span>
                </span>

                <!-- LIVE SPEAKER BADGE -->
                <span id="headerSpeakerBadge" style="display: none; background: rgba(6, 182, 212, 0.2); border: 1px solid #06b6d4; color: #38bdf8; font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 8px; align-items: center; gap: 6px; cursor: pointer;" onclick="openUserProfileMemoryModal('members')">
                    <span style="display: inline-block; width: 7px; height: 7px; background: #06b6d4; border-radius: 50%; animation: pulse 1.5s infinite;"></span>
                    <span>Đang nói: </span><b id="headerSpeakerName">--</b>
                </span>

                <!-- 4. CÀI ĐẶT KỸ THUẬT (Home Assistant, Voice AI, OTA Firmware) -->
                <button type="button" class="btn-hub-nav" onclick="openSystemSettingsModal()" style="background: linear-gradient(135deg, #6366f1, #4f46e5); border: none; color: white; padding: 7px 15px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35); transition: all 0.2s;">
                    ⚙️ Cài Đặt Kỹ Thuật
                </button>'''

m = re.search(old_header_buttons_pattern, content, re.DOTALL)
assert m is not None, "Failed to match old_header_buttons_pattern"
content = content[:m.start()] + new_header_buttons + content[m.end():]
print("✅ Replaced Header Buttons successfully!")

# Write test to inspect
with open('server_nas_hub/app/static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated index.html header")
