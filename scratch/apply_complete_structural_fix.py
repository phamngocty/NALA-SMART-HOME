with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace tab_upm_memory with full 3-column content and correct closure
old_upm_memory = '''                <!-- TAB 3: MEMORY -->
                <div id="tab_upm_memory" style="display: none;">
                    <!-- Metric Badges & Action Bar -->
        <div style="padding: 12px 24px; background: rgba(15, 23, 42, 0.6); border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <span id="badgeAliasCount" style="font-size: 11px; font-weight: 700; color: #38bdf8; background: rgba(56, 189, 248, 0.12); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(56, 189, 248, 0.3);">🏷️ 0/50 Biệt danh</span>
                <span id="badgeHabitCount" style="font-size: 11px; font-weight: 700; color: #f59e0b; background: rgba(245, 158, 11, 0.12); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(245, 158, 11, 0.3);">⏰ 0/30 Thói quen</span>
                <span id="badgeFactCount" style="font-size: 11px; font-weight: 700; color: #10b981; background: rgba(16, 185, 129, 0.12); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.3);">👤 0/20 Thông tin</span>
                <span id="badgeSizeCount" style="font-size: 11px; font-weight: 700; color: #a855f7; background: rgba(168, 85, 247, 0.12); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(168, 85, 247, 0.3);">💾 0 KB</span>
            </div>
            <div style="display: flex; gap: 8px;">
                <label style="display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700; color: #38bdf8; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); padding: 4px 10px; border-radius: 6px; cursor: pointer;">
                    <input type="checkbox" id="chkMemoryEnabled" onchange="toggleMemoryEnabled(this.checked)" style="accent-color: #38bdf8; cursor: pointer;" checked>
                    <span>Tự Học Adaptive Memory</span>
                </label>
                <button onclick="promptAddAlias()" style="background: #0284c7; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">➕ Thêm Biệt Danh</button>
                <button onclick="promptAddFact()" style="background: #059669; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">➕ Thêm Ghi Nhớ</button>
                <button onclick="cleanGarbageMemory()" style="background: #334155; color: #cbd5e1; border: 1px solid #475569; padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">🧹 Dọn Rác</button>
                <button onclick="resetAllMemory()" style="background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">⚠️ Đặt Lại</button>
            </div>
        </div>

        <!-- 3 Columns Content -->
        <div class="modal-body" style="padding: 18px 24px; display: grid; grid-template-columns: 1.1fr 1fr 0.9fr; gap: 16px;">
            <!-- Column 1: Aliases -->
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #334155; border-radius: 10px; padding: 12px; display: flex; flex-direction: column;">
                <div style="font-size: 13px; font-weight: 700; color: #38bdf8; margin-bottom: 8px; display: flex; justify-content: space-between;">
                    <span>🏷️ Biệt Danh Thiết Bị</span>
                    <span style="font-size: 10px; color: #94a3b8;">(Tự nạp Fast-Path)</span>
                </div>
                </div>'''

new_upm_memory = '''                <!-- TAB 3: MEMORY -->
                <div id="tab_upm_memory" style="display: none;">
                    <!-- Metric Badges & Action Bar -->
                    <div style="padding: 12px 24px; background: rgba(15, 23, 42, 0.6); border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                            <span id="badgeAliasCount" style="font-size: 11px; font-weight: 700; color: #38bdf8; background: rgba(56, 189, 248, 0.12); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(56, 189, 248, 0.3);">🏷️ 0/50 Biệt danh</span>
                            <span id="badgeHabitCount" style="font-size: 11px; font-weight: 700; color: #f59e0b; background: rgba(245, 158, 11, 0.12); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(245, 158, 11, 0.3);">⏰ 0/30 Thói quen</span>
                            <span id="badgeFactCount" style="font-size: 11px; font-weight: 700; color: #10b981; background: rgba(16, 185, 129, 0.12); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.3);">👤 0/20 Thông tin</span>
                            <span id="badgeSizeCount" style="font-size: 11px; font-weight: 700; color: #a855f7; background: rgba(168, 85, 247, 0.12); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(168, 85, 247, 0.3);">💾 0 KB</span>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <label style="display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700; color: #38bdf8; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); padding: 4px 10px; border-radius: 6px; cursor: pointer;">
                                <input type="checkbox" id="chkMemoryEnabled" onchange="toggleMemoryEnabled(this.checked)" style="accent-color: #38bdf8; cursor: pointer;" checked>
                                <span>Tự Học Adaptive Memory</span>
                            </label>
                            <button onclick="promptAddAlias()" style="background: #0284c7; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">➕ Thêm Biệt Danh</button>
                            <button onclick="promptAddFact()" style="background: #059669; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">➕ Thêm Ghi Nhớ</button>
                            <button onclick="cleanGarbageMemory()" style="background: #334155; color: #cbd5e1; border: 1px solid #475569; padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">🧹 Dọn Rác</button>
                            <button onclick="resetAllMemory()" style="background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); padding: 6px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">⚠️ Đặt Lại</button>
                        </div>
                    </div>

                    <!-- 3 Columns Content Grid -->
                    <div style="padding: 18px 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px;">
                        <!-- Column 1: Aliases -->
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #334155; border-radius: 10px; padding: 12px; display: flex; flex-direction: column;">
                            <div style="font-size: 13px; font-weight: 700; color: #38bdf8; margin-bottom: 8px; display: flex; justify-content: space-between;">
                                <span>🏷️ Biệt Danh Thiết Bị</span>
                                <span style="font-size: 10px; color: #94a3b8;">(Tự nạp Fast-Path)</span>
                            </div>
                            <div id="memoryAliasesList" style="flex: 1; max-height: 380px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px;">
                                <div style="text-align: center; color: #64748b; font-size: 11px; padding: 20px;">Đang tải...</div>
                            </div>
                        </div>

                        <!-- Column 2: Habits -->
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #334155; border-radius: 10px; padding: 12px; display: flex; flex-direction: column;">
                            <div style="font-size: 13px; font-weight: 700; color: #f59e0b; margin-bottom: 8px; display: flex; justify-content: space-between;">
                                <span>⏰ Thói Quen Theo Giờ</span>
                                <span style="font-size: 10px; color: #94a3b8;">(Dự đoán nhu cầu)</span>
                            </div>
                            <div id="memoryHabitsList" style="flex: 1; max-height: 380px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px;">
                                <div style="text-align: center; color: #64748b; font-size: 11px; padding: 20px;">Đang tải...</div>
                            </div>
                        </div>

                        <!-- Column 3: Facts -->
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #334155; border-radius: 10px; padding: 12px; display: flex; flex-direction: column;">
                            <div style="font-size: 13px; font-weight: 700; color: #10b981; margin-bottom: 8px; display: flex; justify-content: space-between;">
                                <span>👤 Thông Tin Gia Đình</span>
                                <span style="font-size: 10px; color: #94a3b8;">(Ngữ cảnh dài hạn)</span>
                            </div>
                            <div id="memoryFactsList" style="flex: 1; max-height: 380px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px;">
                                <div style="text-align: center; color: #64748b; font-size: 11px; padding: 20px;">Đang tải...</div>
                            </div>
                        </div>
                    </div>
                </div>'''

assert old_upm_memory in content, "old_upm_memory target not found!"
content = content.replace(old_upm_memory, new_upm_memory, 1)

# 2. Fix systemSettingsModal closing divs
old_sys_close = '''                <div id="otaTrackerList" style="display: flex; flex-direction: column; gap: 8px; max-height: 200px; overflow-y: auto;">
                    <div style="font-size: 12px; color: #64748b; font-style: italic;">Chưa có tác vụ OTA nào đang chạy.</div>
                </div>
            </div>

            
</div>
<div class="modal-footer" style="padding: 16px 24px; background: #182234; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">
                <button type="button" class="btn-cancel" onclick="closeSystemSettingsModal()">Đóng</button>
            </div>
        </div>
    </div>'''

new_sys_close = '''                <div id="otaTrackerList" style="display: flex; flex-direction: column; gap: 8px; max-height: 200px; overflow-y: auto;">
                    <div style="font-size: 12px; color: #64748b; font-style: italic;">Chưa có tác vụ OTA nào đang chạy.</div>
                </div>
            </div>
        </div>
    </div>

    <div class="modal-footer" style="padding: 16px 24px; background: #182234; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">
        <button type="button" class="btn-cancel" onclick="closeSystemSettingsModal()">Đóng</button>
    </div>
</div>
</div>'''

assert old_sys_close in content, "old_sys_close target not found!"
content = content.replace(old_sys_close, new_sys_close, 1)

# 3. Remove orphaned legacy memory modal block
old_orphaned = '''    <!-- ======================================================================= -->
<!-- AI AGENT ROUTER & AUDIO PIPELINE CONFIGURATION MODAL -->
<!-- ======================================================================= -->
<!-- aiConfigModal & nalaMemoryModal moved to unified hubs -->
<!-- Column 3: Facts -->
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #334155; border-radius: 10px; padding: 12px; display: flex; flex-direction: column;">
                <div style="font-size: 13px; font-weight: 700; color: #10b981; margin-bottom: 8px; display: flex; justify-content: space-between;">
                    <span>👤 Thông Tin Gia Đình</span>
                    <span style="font-size: 10px; color: #94a3b8;">(Ngữ cảnh dài hạn)</span>
                </div>
                <div id="memoryFactsList" style="flex: 1; max-height: 380px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px;">
                    <div style="text-align: center; color: #64748b; font-size: 11px; padding: 20px;">Đang tải...</div>
                </div>
            </div>
        </div>

        <div class="modal-footer" style="padding: 12px 24px; border-top: 1px solid #1e293b; display: flex; justify-content: flex-end; background: #0f172a;">
            <button onclick="closeMemoryModal()" style="padding: 8px 18px; border-radius: 8px; background: #334155; border: none; color: #f1f5f9; cursor: pointer; font-size: 12px; font-weight: 600;">Đóng</button>
        </div>
    </div>
</div>'''

assert old_orphaned in content, "old_orphaned target not found!"
content = content.replace(old_orphaned, '<!-- Legacy memoryModal cleanup done -->', 1)

with open('server_nas_hub/app/static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("🎉 File index.html successfully updated with complete structural integrity!")
