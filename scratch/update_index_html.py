import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

file_path = "server_nas_hub/app/static/index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add header button
header_btn = '''                <button class="btn-allhouse-header" onclick="openAllHouseConfigModal()" style="background: linear-gradient(135deg, #0284c7, #06b6d4); border: none; color: white; padding: 7px 14px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35);">
                    🏠 Cấu Hình Nút Toàn Nhà
                </button>\n'''

if "btn-allhouse-header" not in content:
    target = '<button class="btn-ha-config"'
    if target in content:
        content = content.replace(target, header_btn + "                " + target, 1)
        print("✓ Added header button")
    else:
        print("✗ Could not find btn-ha-config")

# 2. Add All-House Strip below KPI row
strip_html = '''\n        <!-- All-House Master Status & Quick Control Strip -->
        <div id="allHouseStrip" style="background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.95)); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 12px; padding: 14px 20px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 16px rgba(0,0,0,0.4); flex-wrap: wrap; gap: 12px;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(56, 189, 248, 0.15); display: flex; align-items: center; justify-content: center; font-size: 24px;">
                    🏠
                </div>
                <div>
                    <div style="font-size: 11px; text-transform: uppercase; font-weight: 800; color: #38bdf8; letter-spacing: 0.5px;">Trạng Thái Toàn Bộ Ngôi Nhà (All-House Master)</div>
                    <div id="allHouseSummaryText" style="font-size: 15px; font-weight: 700; color: #f8fafc; margin-top: 2px;">
                        Đang đồng bộ trạng thái...
                    </div>
                </div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <button type="button" onclick="triggerWebMasterOff()" id="btnWebMasterOff" style="background: linear-gradient(135deg, #ef4444, #b91c1c); color: #fff; border: none; padding: 9px 18px; border-radius: 8px; font-weight: 800; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.35); transition: all 0.2s;">
                    🛑 TẮT HẾT TOÀN NHÀ
                </button>
                <button type="button" onclick="openAllHouseConfigModal()" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); padding: 9px 16px; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s;">
                    ⚙️ Cấu Hình Nút
                </button>
            </div>
        </div>\n'''

if "allHouseStrip" not in content:
    target = 'id="unpairedSection"'
    if target in content:
        # insert before unpairedSection
        idx = content.find(target)
        # find the preceding <div or comment
        div_start = content.rfind('<div', 0, idx)
        content = content[:div_start] + strip_html + "        " + content[div_start:]
        print("✓ Added All-House Strip")
    else:
        print("✗ Could not find unpairedSection")

# 3. Add allHouseConfigModal HTML before toast
modal_html = '''    <!-- ======================================================================= -->
    <!-- MODAL CẤU HÌNH NÚT TOÀN NHÀ & TẮT HẾT (ALL-HOUSE MASTER CONFIG MODAL)     -->
    <!-- ======================================================================= -->
    <div class="modal-overlay" id="allHouseConfigModal" style="display: none; align-items: center; justify-content: center; z-index: 10000;">
        <div class="modal-box" style="max-width: 820px; width: 95%; max-height: 90vh; overflow-y: auto; background: #0f172a; border: 1px solid #334155; border-radius: 16px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7); color: #f8fafc;">
            <div class="modal-header" style="padding: 18px 24px; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center; background: #1e293b;">
                <div class="modal-title" style="display: flex; align-items: center; gap: 10px; font-size: 17px; font-weight: 800;">
                    <span style="font-size: 22px;">🏠</span>
                    <span>Cài Đặt Cấu Hình Nút Toàn Nhà & Tắt Hết (Master Control)</span>
                </div>
                <button class="btn-close" onclick="closeAllHouseConfigModal()" style="background: none; border: none; color: #94a3b8; font-size: 24px; cursor: pointer;">&times;</button>
            </div>

            <div class="modal-body" style="padding: 20px 24px; display: flex; flex-direction: column; gap: 20px;">
                <!-- 1. Hướng Dẫn & Giới Thiệu -->
                <div style="background: rgba(56, 189, 248, 0.08); border: 1px dashed rgba(56, 189, 248, 0.4); border-radius: 12px; padding: 14px; font-size: 13px; line-height: 1.5; color: #cbd5e1;">
                    <span style="color: #38bdf8; font-weight: 700;">💡 Nút Toàn Nhà (Tab Toàn Nhà trên màn hình & Web Admin):</span>
                    Cho phép gia chủ chỉ với 1 chạm có thể tắt tất cả thiết bị đang hoạt động khi ra khỏi nhà hoặc đi ngủ. Tại đây, bạn có thể chỉ định chính xác nhóm thiết bị được tắt, kịch bản ngữ cảnh, và danh sách bảo vệ các thiết bị quan trọng (như tủ lạnh, WiFi router) để không bao giờ bị tắt nhầm!
                </div>

                <!-- 2. Chế Độ Hoạt Động (Action Mode) -->
                <div style="background: #182234; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                    <label style="display: block; font-weight: 700; color: #38bdf8; margin-bottom: 12px; font-size: 13px; text-transform: uppercase;">
                        ⚡ 1. Chế Độ Hoạt Động Khi Bấm [TẮT HẾT]:
                    </label>
                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; font-size: 13px; font-weight: 600;">
                            <input type="radio" name="allHouseActionMode" value="turn_off_selected" checked onchange="onAllHouseModeChange()" style="width: 18px; height: 18px; accent-color: #38bdf8;">
                            <span>Tắt trực tiếp các nhóm thiết bị đã chọn bên dưới (Khuyên dùng)</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; font-size: 13px; font-weight: 600;">
                            <input type="radio" name="allHouseActionMode" value="activate_scene" onchange="onAllHouseModeChange()" style="width: 18px; height: 18px; accent-color: #38bdf8;">
                            <span>Kích hoạt Ngữ Cảnh Home Assistant (Home Assistant Scene)</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; font-size: 13px; font-weight: 600;">
                            <input type="radio" name="allHouseActionMode" value="both" onchange="onAllHouseModeChange()" style="width: 18px; height: 18px; accent-color: #38bdf8;">
                            <span>Kết hợp cả hai: Tắt thiết bị đã chọn VÀ Kích hoạt Ngữ Cảnh</span>
                        </label>
                    </div>

                    <!-- Dropdown chọn Scene -->
                    <div id="allHouseSceneRow" style="display: none; margin-top: 14px; padding-top: 12px; border-top: 1px dashed #334155;">
                        <label style="display: block; font-size: 12px; font-weight: 700; color: #a78bfa; margin-bottom: 6px;">
                            🎬 Chọn Ngữ Cảnh Home Assistant (Scene):
                        </label>
                        <select id="allHouseSceneSelect" style="width: 100%; background: #0f172a; border: 1px solid #475569; color: #fff; border-radius: 8px; padding: 9px 12px; font-size: 13px;">
                            <option value="">-- Không sử dụng scene --</option>
                        </select>
                    </div>
                </div>

                <!-- 3. Nhóm Thiết Bị Được Phép Tắt (Controlled Domains) -->
                <div id="allHouseDomainsCard" style="background: #182234; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                    <label style="display: block; font-weight: 700; color: #38bdf8; margin-bottom: 12px; font-size: 13px; text-transform: uppercase;">
                        🎛️ 2. Các Nhóm Thiết Bị Chịu Tác Động:
                    </label>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
                        <label style="display: flex; align-items: center; gap: 10px; background: #0f172a; border: 1px solid #334155; padding: 12px; border-radius: 8px; cursor: pointer;">
                            <input type="checkbox" id="chkDomainLight" checked style="width: 18px; height: 18px; accent-color: #fbbf24;">
                            <div>
                                <div style="font-weight: 700; color: #fbbf24; font-size: 13px;">💡 Đèn (light)</div>
                                <div style="font-size: 11px; color: #94a3b8;">Tất cả đèn trần, đèn hắt, rọi</div>
                            </div>
                        </label>

                        <label style="display: flex; align-items: center; gap: 10px; background: #0f172a; border: 1px solid #334155; padding: 12px; border-radius: 8px; cursor: pointer;">
                            <input type="checkbox" id="chkDomainFan" checked style="width: 18px; height: 18px; accent-color: #38bdf8;">
                            <div>
                                <div style="font-weight: 700; color: #38bdf8; font-size: 13px;">🌀 Quạt (fan)</div>
                                <div style="font-size: 11px; color: #94a3b8;">Tất cả quạt trần, quạt hút</div>
                            </div>
                        </label>

                        <label style="display: flex; align-items: center; gap: 10px; background: #0f172a; border: 1px solid #334155; padding: 12px; border-radius: 8px; cursor: pointer;">
                            <input type="checkbox" id="chkDomainClimate" style="width: 18px; height: 18px; accent-color: #60a5fa;">
                            <div>
                                <div style="font-weight: 700; color: #60a5fa; font-size: 13px;">❄️ Máy Lạnh (climate)</div>
                                <div style="font-size: 11px; color: #94a3b8;">Tắt điều hòa khi ra khỏi nhà</div>
                            </div>
                        </label>

                        <label style="display: flex; align-items: center; gap: 10px; background: #0f172a; border: 1px solid #334155; padding: 12px; border-radius: 8px; cursor: pointer;">
                            <input type="checkbox" id="chkDomainSwitch" style="width: 18px; height: 18px; accent-color: #a3e635;">
                            <div>
                                <div style="font-weight: 700; color: #a3e635; font-size: 13px;">🔌 Công Tắc Phụ (switch)</div>
                                <div style="font-size: 11px; color: #94a3b8;">Ổ cắm, công tắc phụ trợ</div>
                            </div>
                        </label>
                    </div>
                </div>

                <!-- 4. Danh Sách Thiết Bị Loại Trừ (Excluded Entities - An Toàn Tuyệt Đối) -->
                <div style="background: #182234; border: 1px solid #334155; border-radius: 12px; padding: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 12px;">
                        <div>
                            <label style="font-weight: 700; color: #f87171; font-size: 13px; text-transform: uppercase;">
                                🛡️ 3. Danh Sách Thiết Bị Loại Trừ (Bảo Vệ An Toàn):
                            </label>
                            <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                                Thiết bị được TÍCH CHỌN sẽ KHÔNG BAO GIỜ bị tắt khi bấm [TẮT HẾT] và không bị tính vào số lượng đèn/quạt đang bật!
                            </div>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <input type="text" id="allHouseExcludeSearch" placeholder="🔍 Tìm thiết bị hoặc phòng..." oninput="renderAllHouseExcludedList()" style="background: #0f172a; border: 1px solid #475569; color: #fff; border-radius: 6px; padding: 6px 10px; font-size: 12px; width: 200px;">
                            <button type="button" onclick="clearAllExcludedEntities()" style="background: #334155; border: none; color: #cbd5e1; border-radius: 6px; padding: 6px 10px; font-size: 11px; cursor: pointer;">Bỏ chọn hết</button>
                        </div>
                    </div>

                    <!-- Scrollable Entity Checklist -->
                    <div id="allHouseExcludedContainer" style="max-height: 280px; overflow-y: auto; background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 10px; display: flex; flex-direction: column; gap: 6px;">
                        <div style="text-align: center; color: #94a3b8; padding: 20px; font-size: 12px;">Đang tải danh sách thiết bị từ Home Assistant...</div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 11px; color: #94a3b8;">
                        <span id="allHouseExcludedCountBadge">Đã bảo vệ: 0 thiết bị</span>
                        <span>* Thích hợp cho: Tủ lạnh, WiFi Router, Camera an ninh, Máy lọc hồ cá...</span>
                    </div>
                </div>

                <!-- 5. Tùy Chọn Xác Nhận -->
                <div style="background: #182234; border: 1px solid #334155; border-radius: 12px; padding: 14px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 700; color: #f8fafc; font-size: 13px;">Hỏi Xác Nhận Trước Khi Tắt Trên Web</div>
                        <div style="font-size: 11px; color: #94a3b8;">Hiển thị popup cảnh báo xác nhận khi admin bấm [TẮT HẾT] trên trình duyệt</div>
                    </div>
                    <input type="checkbox" id="chkAllHouseConfirm" style="width: 20px; height: 20px; accent-color: #38bdf8;">
                </div>
            </div>

            <div class="modal-footer" style="padding: 16px 24px; border-top: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center; background: #1e293b;">
                <button type="button" onclick="triggerWebMasterOff(true)" style="background: linear-gradient(135deg, #ef4444, #b91c1c); color: white; border: none; padding: 9px 18px; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                    🛑 Bấm Thử Nghiệm Tắt Hết
                </button>
                <div style="display: flex; gap: 12px;">
                    <button type="button" class="btn-cancel" onclick="closeAllHouseConfigModal()" style="padding: 9px 18px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer;">Đóng</button>
                    <button type="button" class="btn-primary" onclick="saveAllHouseConfig()" style="background: linear-gradient(135deg, #0284c7, #06b6d4); color: white; border: none; padding: 9px 22px; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);">💾 Lưu Cấu Hình Toàn Nhà</button>
                </div>
            </div>
        </div>
    </div>\n\n'''

if "allHouseConfigModal" not in content:
    target = '<div class="toast" id="toastMsg">'
    if target in content:
        content = content.replace(target, modal_html + "    " + target, 1)
        print("✓ Added allHouseConfigModal")
    else:
        print("✗ Could not find toastMsg")

# 4. Add JavaScript
js_code = '''
        // =========================================================================
        // ALL-HOUSE MASTER CONFIGURATION & CONTROL
        // =========================================================================
        let allHouseConfig = {
            enabled: true,
            action_mode: "turn_off_selected",
            controlled_domains: ["light", "fan"],
            include_climate: false,
            include_switch: false,
            excluded_entities: [],
            scene_entity_id: "",
            confirm_prompt: false
        };
        let allHouseScenes = [];
        let allHouseAvailableEntities = [];

        async function loadAllHouseStatus() {
            try {
                const res = await fetch('/api/all-house/config');
                if (!res.ok) return;
                const data = await res.json();
                allHouseConfig = data.config || allHouseConfig;
                allHouseScenes = data.scenes || [];
                updateAllHouseStrip(data.house_status);
            } catch (e) {
                console.error("Error loading all-house status:", e);
            }
        }

        function updateAllHouseStrip(status) {
            const strip = document.getElementById('allHouseSummaryText');
            if (!strip) return;
            if (!status) {
                strip.textContent = "Chưa có dữ liệu trạng thái";
                return;
            }
            const total = status.total_on_devices || 0;
            const summary = status.summary_text || (total > 0 ? `${total} thiết bị đang bật` : "ĐÃ TẮT HẾT CÁC PHÒNG");
            if (total > 0) {
                strip.innerHTML = `<span style="color: #fbbf24; font-weight: 800;">⚠️ ${summary}</span>`;
            } else {
                strip.innerHTML = `<span style="color: #10b981; font-weight: 800;">✓ ${summary}</span>`;
            }
        }

        async function openAllHouseConfigModal() {
            const modal = document.getElementById('allHouseConfigModal');
            if (!modal) return;
            modal.style.display = 'flex';
            
            try {
                const [cfgRes, entRes] = await Promise.all([
                    fetch('/api/all-house/config'),
                    fetch('/api/ha/entities')
                ]);
                
                if (cfgRes.ok) {
                    const cfgData = await cfgRes.json();
                    allHouseConfig = cfgData.config || allHouseConfig;
                    allHouseScenes = cfgData.scenes || [];
                }
                
                if (entRes.ok) {
                    allHouseAvailableEntities = await entRes.json();
                }
            } catch (err) {
                console.error("Error fetching config or entities:", err);
            }

            const modeRadios = document.getElementsByName('allHouseActionMode');
            for (let r of modeRadios) {
                r.checked = (r.value === (allHouseConfig.action_mode || 'turn_off_selected'));
            }
            onAllHouseModeChange();

            const sceneSelect = document.getElementById('allHouseSceneSelect');
            if (sceneSelect) {
                sceneSelect.innerHTML = '<option value="">-- Không sử dụng scene --</option>';
                allHouseScenes.forEach(sc => {
                    const opt = document.createElement('option');
                    opt.value = sc.entity_id;
                    opt.textContent = `${sc.friendly_name} (${sc.entity_id})`;
                    if (sc.entity_id === allHouseConfig.scene_entity_id) {
                        opt.selected = true;
                    }
                    sceneSelect.appendChild(opt);
                });
            }

            const domains = allHouseConfig.controlled_domains || ['light', 'fan'];
            if (document.getElementById('chkDomainLight')) document.getElementById('chkDomainLight').checked = domains.includes('light');
            if (document.getElementById('chkDomainFan')) document.getElementById('chkDomainFan').checked = domains.includes('fan');
            if (document.getElementById('chkDomainClimate')) document.getElementById('chkDomainClimate').checked = !!allHouseConfig.include_climate;
            if (document.getElementById('chkDomainSwitch')) document.getElementById('chkDomainSwitch').checked = !!allHouseConfig.include_switch;
            if (document.getElementById('chkAllHouseConfirm')) document.getElementById('chkAllHouseConfirm').checked = !!allHouseConfig.confirm_prompt;

            renderAllHouseExcludedList();
        }

        function closeAllHouseConfigModal() {
            const modal = document.getElementById('allHouseConfigModal');
            if (modal) modal.style.display = 'none';
        }

        function onAllHouseModeChange() {
            const selectedMode = document.querySelector('input[name="allHouseActionMode"]:checked')?.value || 'turn_off_selected';
            const sceneRow = document.getElementById('allHouseSceneRow');
            const domainsCard = document.getElementById('allHouseDomainsCard');
            if (sceneRow) {
                sceneRow.style.display = (selectedMode === 'activate_scene' || selectedMode === 'both') ? 'block' : 'none';
            }
            if (domainsCard) {
                domainsCard.style.opacity = (selectedMode === 'activate_scene') ? '0.5' : '1';
            }
        }

        function renderAllHouseExcludedList() {
            const container = document.getElementById('allHouseExcludedContainer');
            if (!container) return;
            const search = (document.getElementById('allHouseExcludeSearch')?.value || '').toLowerCase().trim();
            const excludedSet = new Set(allHouseConfig.excluded_entities || []);

            let list = allHouseAvailableEntities.filter(e => {
                const dom = e.domain || (e.entity_id.split('.')[0]);
                return ['light', 'fan', 'climate', 'switch'].includes(dom);
            });

            if (search) {
                list = list.filter(e => {
                    const name = (e.friendly_name || '').toLowerCase();
                    const id = (e.entity_id || '').toLowerCase();
                    const area = (e.area_name || '').toLowerCase();
                    return name.includes(search) || id.includes(search) || area.includes(search);
                });
            }

            if (list.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #94a3b8; padding: 20px; font-size: 12px;">Không tìm thấy thiết bị phù hợp.</div>';
                return;
            }

            let html = '';
            list.forEach(item => {
                const isExcluded = excludedSet.has(item.entity_id);
                const areaBadge = item.area_name ? `<span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-size: 10px;">📍 ${escapeHtml(item.area_name)}</span>` : '';
                const domBadge = `<span style="background: #1e293b; color: #94a3b8; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-family: monospace;">${escapeHtml(item.domain || item.entity_id.split('.')[0])}</span>`;
                
                html += `
                <label style="display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; background: ${isExcluded ? 'rgba(239, 68, 68, 0.12)' : '#111827'}; border: 1px solid ${isExcluded ? 'rgba(239, 68, 68, 0.4)' : '#1f2937'}; border-radius: 6px; cursor: pointer; transition: all 0.15s;">
                    <div style="display: flex; align-items: center; gap: 10px; overflow: hidden;">
                        <input type="checkbox" ${isExcluded ? 'checked' : ''} onchange="toggleExcludeEntity('${escapeHtml(item.entity_id)}', this.checked)" style="width: 16px; height: 16px; accent-color: #ef4444;">
                        <div style="overflow: hidden;">
                            <div style="font-weight: 600; font-size: 12px; color: ${isExcluded ? '#fca5a5' : '#f8fafc'}; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">
                                ${escapeHtml(item.friendly_name || item.entity_id)}
                            </div>
                            <div style="font-size: 10px; color: #64748b; font-family: monospace;">${escapeHtml(item.entity_id)}</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        ${areaBadge}
                        ${domBadge}
                        <span style="font-size: 11px; font-weight: 700; color: ${isExcluded ? '#f87171' : '#64748b'};">
                            ${isExcluded ? '🛡️ ĐÃ BẢO VỆ' : 'Bình thường'}
                        </span>
                    </div>
                </label>
                `;
            });

            container.innerHTML = html;
            const badge = document.getElementById('allHouseExcludedCountBadge');
            if (badge) {
                badge.textContent = `Đã bảo vệ: ${excludedSet.size} thiết bị`;
            }
        }

        function toggleExcludeEntity(entityId, isExcluded) {
            let set = new Set(allHouseConfig.excluded_entities || []);
            if (isExcluded) {
                set.add(entityId);
            } else {
                set.delete(entityId);
            }
            allHouseConfig.excluded_entities = Array.from(set);
            renderAllHouseExcludedList();
        }

        function clearAllExcludedEntities() {
            allHouseConfig.excluded_entities = [];
            renderAllHouseExcludedList();
        }

        async function saveAllHouseConfig() {
            const selectedMode = document.querySelector('input[name="allHouseActionMode"]:checked')?.value || 'turn_off_selected';
            const sceneId = document.getElementById('allHouseSceneSelect')?.value || '';
            
            const controlledDomains = [];
            if (document.getElementById('chkDomainLight')?.checked) controlledDomains.push('light');
            if (document.getElementById('chkDomainFan')?.checked) controlledDomains.push('fan');

            const payload = {
                enabled: true,
                action_mode: selectedMode,
                controlled_domains: controlledDomains,
                include_climate: !!document.getElementById('chkDomainClimate')?.checked,
                include_switch: !!document.getElementById('chkDomainSwitch')?.checked,
                excluded_entities: allHouseConfig.excluded_entities || [],
                scene_entity_id: sceneId,
                confirm_prompt: !!document.getElementById('chkAllHouseConfirm')?.checked,
                alert_title: "TOÀN BỘ NHÀ"
            };

            try {
                const res = await fetch('/api/all-house/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const resData = await res.json();
                if (res.ok && resData.status === 'success') {
                    showToast('✓ Cấu hình nút Toàn Nhà đã được lưu và đồng bộ!');
                    allHouseConfig = payload;
                    if (resData.house_status) {
                        updateAllHouseStrip(resData.house_status);
                    }
                    closeAllHouseConfigModal();
                } else {
                    alert('Lỗi lưu cấu hình: ' + (resData.message || 'Không rõ nguyên nhân'));
                }
            } catch (err) {
                console.error("Save all house config error:", err);
                alert('Lỗi kết nối tới máy chủ khi lưu cấu hình.');
            }
        }

        async function triggerWebMasterOff(fromModal = false) {
            if (allHouseConfig.confirm_prompt && !fromModal) {
                if (!confirm("Bạn có chắc chắn muốn TẮT HẾT toàn bộ thiết bị đang bật trong nhà không?")) {
                    return;
                }
            }

            try {
                const res = await fetch('/api/all-house/master-off', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    const count = data.result?.turned_off_count || 0;
                    showToast(`✓ Đã thực thi Tắt Hết! ${count} thiết bị đã tắt.`);
                    if (data.house_status) {
                        updateAllHouseStrip(data.house_status);
                    }
                } else {
                    alert('Lỗi kích hoạt Master Off: ' + (data.message || 'Thất bại'));
                }
            } catch (err) {
                console.error("Master off trigger error:", err);
                alert('Lỗi kết nối máy chủ khi bấm tắt hết.');
            }
        }
'''

if "ALL-HOUSE MASTER CONFIGURATION & CONTROL" not in content:
    target = 'function handleWSMessage(data)'
    if target in content:
        content = content.replace(target, js_code + "\n        " + target, 1)
        print("✓ Added JS code")
    else:
        print("✗ Could not find handleWSMessage")

# 5. Handle WebSocket message for house_status_update
ws_update_code = '''            } else if (type === 'house_status_update') {
                if (data.payload) {
                    updateAllHouseStrip(data.payload);
                }
'''

if "type === 'house_status_update'" not in content:
    target = "} else if (type === 'intercom_sync') {"
    if target in content:
        content = content.replace(target, ws_update_code + "            " + target, 1)
        print("✓ Added WebSocket house_status_update handling")
    else:
        print("✗ Could not find intercom_sync in handleWSMessage")

# 6. Call loadAllHouseStatus() in startApp
if "loadAllHouseStatus()" not in content:
    target = "initWebSocket();"
    if target in content:
        # replace the one inside startApp
        content = content.replace(target, target + "\n            loadAllHouseStatus();", 1)
        print("✓ Added loadAllHouseStatus to startup")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("index.html update successfully finished!")

