
        // Global App State
        let currentDevices = [];
        let currentEntities = [];
        let entityStates = {}; // entity_id -> state ("on" / "off")
        let ws = null;
        let wsReconnectTimer = null;

        // HA Metadata & Active Area Filter
        let haAreasList = [];
        let haFloorsList = [];
        let currentSelectedAreaId = "";

        // OTA Real-time Trackers
        let activeOtaPanels = {}; // code -> { progress, status, message }

        // Active Wizard Working Buttons List
        let wizardButtons = [];
        let activeWizardDevice = null;

        function showToast(text, isError = false) {
            const t = document.getElementById('toastMsg');
            t.textContent = text;
            t.style.background = isError ? '#ef4444' : '#10b981';
            t.style.color = isError ? '#fff' : '#000';
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 3000);
        }

        // -------------------------------------------------------------------------
        // 1. WEBSOCKET REALTIME CONNECTION
        // -------------------------------------------------------------------------
        function initWebSocket() {
            if (wsReconnectTimer) clearTimeout(wsReconnectTimer);

            const clientId = 'web_admin_' + Math.random().toString(36).substring(2, 8);
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${location.host}/ws/${clientId}`;

            const wsDot = document.getElementById('wsDot');
            const wsText = document.getElementById('wsText');

            wsText.textContent = "WS: Đang kết nối...";
            wsDot.className = "status-dot yellow";

            try {
                ws = new WebSocket(wsUrl);
                ws.binaryType = 'arraybuffer';

                ws.onopen = () => {
                    console.log("[WS] Connected to NALA Central Hub:", wsUrl);
                    wsText.innerHTML = "WS REALTIME: <strong>KẾT NỐI</strong>";
                    wsDot.className = "status-dot";
                };

                ws.onmessage = (event) => {
                    if (event.data instanceof ArrayBuffer) {
                        handleIncomingBinaryPacket(event.data);
                        return;
                    }
                    try {
                        const data = JSON.parse(event.data);
                        handleWSMessage(data);
                    } catch (e) {
                        console.error("[WS] Parse error:", e, event.data);
                    }
                };

                ws.onclose = () => {
                    console.warn("[WS] Disconnected. Reconnecting in 2s...");
                    wsText.textContent = "WS: MẤT KẾT NỐI (Thử lại...)";
                    wsDot.className = "status-dot red";
                    wsReconnectTimer = setTimeout(initWebSocket, 2000);
                };

                ws.onerror = (err) => {
                    console.error("[WS] Socket error:", err);
                    ws.close();
                };

            } catch (e) {
                console.error("[WS] Init error:", e);
                wsReconnectTimer = setTimeout(initWebSocket, 3000);
            }
        }

        
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

        // =========================================================================
        // PHƯƠNG ÁN 1: CÂY PHÂN TẦNG THÔNG MINH (SMART FLOOR & ROOM HUB)
        // =========================================================================
        let currentFloorsOverview = null;
        let expandedFloorMap = { 'tang1': true, 'tang2': true, 'tret': true, 'tang_3': true, 'other': false };
        let expandedAreaMap = {};

        function updateFloorsOverview(data) {
            if (!data) return;
            currentFloorsOverview = data;
            renderFloorsTree(data);
        }

        function toggleFloorExpand(floorId) {
            expandedFloorMap[floorId] = (expandedFloorMap[floorId] === undefined) ? false : !expandedFloorMap[floorId];
            if (currentFloorsOverview) renderFloorsTree(currentFloorsOverview);
        }

        function toggleAreaExpand(areaId) {
            expandedAreaMap[areaId] = !expandedAreaMap[areaId];
            if (currentFloorsOverview) renderFloorsTree(currentFloorsOverview);
        }

        async function turnOffFloor(floorId, floorName) {
            if (!confirm(`Xác nhận tắt TOÀN BỘ thiết bị đang bật tại [${floorName}]?`)) return;
            try {
                const res = await fetch('/api/all-house/turn-off-floor', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ floor_id: floorId })
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    showToast(`✓ Đã tắt ${data.turned_off_count} thiết bị tại [${floorName}]!`);
                    if (data.floors_overview) updateFloorsOverview(data.floors_overview);
                    if (data.house_status) updateAllHouseStrip(data.house_status);
                } else {
                    showToast('Lỗi khi tắt tầng', true);
                }
            } catch (e) {
                console.error("turnOffFloor error:", e);
                showToast('Lỗi kết nối máy chủ', true);
            }
        }

        async function turnOffArea(areaId, areaName) {
            try {
                const res = await fetch('/api/all-house/turn-off-area', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ area_id: areaId })
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    showToast(`✓ Đã tắt ${data.turned_off_count} thiết bị tại [${areaName}]!`);
                    if (data.floors_overview) updateFloorsOverview(data.floors_overview);
                    if (data.house_status) updateAllHouseStrip(data.house_status);
                } else {
                    showToast('Lỗi khi tắt phòng', true);
                }
            } catch (e) {
                console.error("turnOffArea error:", e);
                showToast('Lỗi kết nối máy chủ', true);
            }
        }

        function renderFloorsTree(data) {
            const container = document.getElementById('allHouseFloorsContainer');
            if (!container) return;
            const floors = (data && data.floors) ? data.floors : [];
            if (floors.length === 0) {
                container.innerHTML = `<div style="grid-column: 1 / -1; color: #94a3b8; font-size: 13px; font-style: italic; padding: 12px;">Đang đồng bộ cây phân tầng từ Home Assistant...</div>`;
                return;
            }

            container.innerHTML = floors.map(fl => {
                const hasActive = fl.active_count > 0;
                const isExpanded = (expandedFloorMap[fl.floor_id] !== false);
                const borderStyle = hasActive
                    ? 'border: 1px solid rgba(245, 158, 11, 0.45); background: rgba(30, 41, 59, 0.75); box-shadow: 0 4px 16px rgba(245, 158, 11, 0.08);'
                    : 'border: 1px solid rgba(255, 255, 255, 0.08); background: rgba(15, 23, 42, 0.6);';

                const badgeHtml = hasActive
                    ? `<span style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 800; display: inline-flex; align-items: center; gap: 4px;">🟡 ${fl.active_count} BẬT</span>`
                    : `<span style="background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">🟢 Đã tắt hết</span>`;

                const turnOffFloorBtn = hasActive
                    ? `<button type="button" onclick="event.stopPropagation(); turnOffFloor('${fl.floor_id}', '${escapeHtml(fl.floor_name)}')" style="background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; border: none; padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 11px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);">⚡ Tắt Tầng</button>`
                    : '';

                const areasHtml = (fl.areas || []).map(ar => {
                    const arActive = ar.active_count > 0;
                    const arExpanded = !!expandedAreaMap[ar.area_id];
                    const activeEntities = (ar.entities || []).filter(e => e.is_on);
                    const inactiveEntities = (ar.entities || []).filter(e => !e.is_on);

                    const activePillsHtml = activeEntities.map(e => `
                        <button type="button" class="entity-btn on-${e.domain}" onclick="event.stopPropagation(); toggleEntity('${escapeHtml(e.entity_id)}')" style="padding: 4px 10px; font-size: 11px; display: inline-flex; align-items: center; gap: 5px; margin: 2px; border-radius: 6px; font-weight: 600;" title="Bấm để TẮT ngay">
                            <span>${getIconForDomain(e.domain)}</span>
                            <span style="max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(e.name)}</span>:
                            <strong style="color: #fff;">BẬT</strong> ✕
                        </button>
                    `).join('');

                    const moreEntitiesHtml = (arExpanded && inactiveEntities.length > 0) ? `
                        <div style="margin-top: 6px; padding-top: 6px; border-top: 1px dashed rgba(255, 255, 255, 0.08); display: flex; flex-wrap: wrap; gap: 4px;">
                            ${inactiveEntities.map(e => `
                                <button type="button" class="entity-btn" onclick="event.stopPropagation(); toggleEntity('${escapeHtml(e.entity_id)}')" style="padding: 3px 8px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px; border-radius: 6px; opacity: 0.7;" title="Bấm để BẬT">
                                    <span>${getIconForDomain(e.domain)}</span>
                                    <span style="max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(e.name)}</span>:
                                    <span>TẮT</span>
                                </button>
                            `).join('')}
                        </div>
                    ` : '';

                    const toggleMoreBtn = (inactiveEntities.length > 0) ? `
                        <button type="button" onclick="event.stopPropagation(); toggleAreaExpand('${ar.area_id}')" style="background: none; border: none; color: #38bdf8; font-size: 11px; cursor: pointer; padding: 2px 4px; text-decoration: underline;">
                            ${arExpanded ? '▲ Thu gọn' : `+ Xem ${inactiveEntities.length} nút khác`}
                        </button>
                    ` : '';

                    return `
                        <div style="background: ${arActive ? 'rgba(15, 23, 42, 0.7)' : 'rgba(255, 255, 255, 0.02)'}; border: 1px solid ${arActive ? 'rgba(245, 158, 11, 0.3)' : 'rgba(255, 255, 255, 0.05)'}; border-radius: 8px; padding: 9px 12px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: ${activeEntities.length > 0 ? '6px' : '0'};">
                                <div style="display: flex; align-items: center; gap: 6px; font-weight: 700; font-size: 13px; color: ${arActive ? '#fef08a' : '#cbd5e1'};">
                                    <span>${arActive ? '📍' : '▫️'}</span>
                                    <span>${escapeHtml(ar.name)}</span>
                                </div>
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    ${arActive ? `
                                        <span style="color: #fbbf24; font-weight: 700; font-size: 11px;">${ar.active_count} bật</span>
                                        <button type="button" onclick="event.stopPropagation(); turnOffArea('${ar.area_id}', '${escapeHtml(ar.name)}')" style="background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: 700; cursor: pointer;">Tắt Phòng</button>
                                    ` : `
                                        <span style="color: #64748b; font-size: 11px;">Đã tắt hết</span>
                                    `}
                                </div>
                            </div>
                            ${activePillsHtml ? `<div style="display: flex; flex-wrap: wrap; gap: 4px; align-items: center;">${activePillsHtml} ${toggleMoreBtn}</div>` : (toggleMoreBtn ? `<div style="margin-top: 4px;">${toggleMoreBtn}</div>` : '')}
                            ${moreEntitiesHtml}
                        </div>
                    `;
                }).join('');

                return `
                    <div style="${borderStyle} border-radius: 12px; padding: 14px; display: flex; flex-direction: column;">
                        <div onclick="toggleFloorExpand('${fl.floor_id}')" style="display: flex; justify-content: space-between; align-items: center; cursor: pointer; user-select: none; padding-bottom: ${isExpanded ? '10px' : '0'}; ${isExpanded ? 'border-bottom: 1px solid rgba(255, 255, 255, 0.08); margin-bottom: 12px;' : ''}">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 15px; font-weight: 800; color: #f8fafc; letter-spacing: 0.5px;">${escapeHtml(fl.floor_name)}</span>
                                ${badgeHtml}
                            </div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                ${turnOffFloorBtn}
                                <span style="color: #94a3b8; font-size: 12px;">${isExpanded ? '▲' : '▼'}</span>
                            </div>
                        </div>
                        ${isExpanded ? `<div>${areasHtml}</div>` : ''}
                    </div>
                `;
            }).join('');
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

        function handleWSMessage(data) {
            const type = data.type;

            if (type === 'init') {
                if (data.system) updateSystemStatus(data.system);
                if (data.floors) haFloorsList = data.floors;
                if (data.areas) haAreasList = data.areas;
                if (data.entities) {
                    currentEntities = data.entities;
                    data.entities.forEach(e => { entityStates[e.entity_id] = e.state; });
                    populateHAEntityDropdown();
                }
                if (data.devices) {
                    currentDevices = data.devices;
                    renderDevices();
                }
                if (data.intercom_targets) {
                    currentIntercomTargets = data.intercom_targets;
                    renderIntercomTargets();
                }
                if (data.house_status) updateAllHouseStrip(data.house_status);
                if (data.floors_overview) updateFloorsOverview(data.floors_overview);
            } else if (type === 'devices_update') {
                currentDevices = data.devices || [];
                renderDevices();
                if (data.intercom_targets) {
                    currentIntercomTargets = data.intercom_targets;
                    renderIntercomTargets();
                }
            } else if (type === 'house_status_update') {
                if (data.payload) {
                    updateAllHouseStrip(data.payload);
                }
                if (data.floors_overview) {
                    updateFloorsOverview(data.floors_overview);
                }
            } else if (type === 'intercom_sync') {
                if (data.payload && data.payload.targets) {
                    currentIntercomTargets = data.payload.targets;
                    renderIntercomTargets();
                }
            } else if (type === 'ha_state_change') {
                const payload = data.payload || {};
                const eid = payload.entity_id;
                const state = payload.state;
                if (eid) {
                    entityStates[eid] = state;
                    updateEntityButtons(eid, state);
                }
                if (payload.house_status) {
                    updateAllHouseStrip(payload.house_status);
                }
                if (payload.floors_overview) {
                    updateFloorsOverview(payload.floors_overview);
                }
            } else if (type === 'ota_progress') {
                handleOtaProgress(data);
            } else if (type === 'ota_started') {
                showToast(`🚀 Đã phát lệnh OTA tới [${data.target}] (${data.sent_count} màn hình)!`);
            } else if (type === 'ota_firmware_uploaded') {
                showToast(`✓ Đã tải lên firmware mới [${data.meta.version}]`);
                loadOtaStatus();
            } else if (type === 'history_new') {
                handleNewHistoryRecord(data.record);
            } else if (type === 'history_cleared' || type === 'history_deleted') {
                if (isHistoryModalOpen) loadHistoryData();
            }
        }

        // -------------------------------------------------------------------------
        // 2. RENDERING LOGIC
        // -------------------------------------------------------------------------
        function updateSystemStatus(sys) {
            const haDot = document.getElementById('haStatusDot');
            const haText = document.getElementById('haStatusText');
            if (sys.ha_connected) {
                haDot.className = "status-dot";
                haText.innerHTML = "HA Pi 5: <strong>Đã Kết Nối</strong>";
            } else {
                haDot.className = "status-dot yellow";
                haText.innerHTML = "HA Pi 5: <strong>Chờ Token / Offline</strong>";
            }
        }

        function getIconForDomain(iconType) {
            switch (iconType) {
                case 'light': return '💡';
                case 'fan': return '🌀';
                case 'climate': return '❄️';
                case 'switch': return '🔌';
                case 'cover': return '🪟';
                case 'scene': return '✨';
                default: return '⚡';
            }
        }

        function renderDevices() {
            const unpaired = currentDevices.filter(d => !d.is_paired);
            const paired = currentDevices.filter(d => d.is_paired);

            // Update KPI
            document.getElementById('kpiTotal').innerHTML = `${currentDevices.length} <span class="sub">thiết bị</span>`;
            document.getElementById('kpiOnline').innerHTML = `${currentDevices.filter(d => d.online).length} <span class="sub" style="color: #10b981;">hoạt động</span>`;
            document.getElementById('kpiPaired').innerHTML = `${paired.length} <span class="sub" style="color: #38bdf8;">phòng</span>`;
            document.getElementById('kpiUnpaired').innerHTML = `${unpaired.length} <span class="sub" style="color: #fbbf24;">mới</span>`;

            // 1. Render Unpaired Section
            document.getElementById('unpairedCount').textContent = `${unpaired.length} Thiết bị`;
            const unpairedGrid = document.getElementById('unpairedGrid');
            if (unpaired.length === 0) {
                unpairedGrid.innerHTML = `
                    <div class="empty-unpaired" style="grid-column: 1 / -1;">
                        ✨ Không có màn hình mới nào đang chờ ghép nối. Khi cấp nguồn cho màn hình mới kết nối WiFi, thiết bị sẽ tự động xuất hiện tại đây.
                    </div>
                `;
            } else {
                unpairedGrid.innerHTML = unpaired.map(d => `
                    <div class="unpaired-card">
                        <div class="unpaired-info">
                            <h3>Màn Hình Panel 2.8" (${escapeHtml(d.model || 'ES3C28P')})</h3>
                            <p>MÃ: <strong style="color: #fbbf24; font-size: 14px;">${escapeHtml(d.pairing_code)}</strong> | MAC: ${escapeHtml(d.mac)}</p>
                            <p style="color: #94a3b8; font-size: 11px; margin-top: 3px;">IP: ${escapeHtml(d.ip)} • FW: <strong style="color: #c084fc;">${escapeHtml(d.firmware_version || 'v3.0.0')}</strong> • Đang chờ cài đặt</p>
                        </div>
                        <button class="btn-pair" onclick="openInstallerWizard('${escapeHtml(d.pairing_code)}')">
                            🛠️ CÀI ĐẶT NGAY
                        </button>
                    </div>
                `).join('');
            }

            // 2. Render Paired Section
            document.getElementById('pairedCount').textContent = `${paired.length} Phòng`;
            const pairedGrid = document.getElementById('pairedGrid');
            if (paired.length === 0) {
                pairedGrid.innerHTML = `
                    <div class="empty-unpaired" style="grid-column: 1 / -1;">
                        Chưa có màn hình gắn tường nào được ghép nối. Hãy chọn ghép nối từ danh sách màn hình mới phía trên.
                    </div>
                `;
            } else {
                pairedGrid.innerHTML = paired.map(d => {
                    const isOnline = d.online;
                    const buttons = d.buttons && d.buttons.length > 0 ? d.buttons : (
                        (d.entities || []).map((eid, idx) => ({
                            id: `btn_${idx+1}`,
                            name: eid.split('.')[1] || eid,
                            entity_id: eid,
                            icon: eid.split('.')[0]
                        }))
                    );

                    const entityBtnsHtml = buttons.map(b => {
                        const eid = b.entity_id;
                        const st = entityStates[eid] || 'off';
                        const isOn = st === 'on' || (st !== 'off' && st !== 'unavailable');
                        let btnClass = 'entity-btn';
                        let icon = getIconForDomain(b.icon || eid.split('.')[0]);

                        if (b.icon === 'light' || eid.startsWith('light')) {
                            if (isOn) btnClass += ' on-light';
                        } else if (b.icon === 'fan' || eid.startsWith('fan')) {
                            if (isOn) btnClass += ' on-fan';
                        } else if (b.icon === 'climate' || eid.startsWith('climate')) {
                            if (isOn) btnClass += ' on-climate';
                        } else {
                            if (isOn) btnClass += ' on-switch';
                        }

                        return `
                            <button class="${btnClass}" data-entity-id="${escapeHtml(eid)}" onclick="toggleEntity('${escapeHtml(eid)}')" title="${escapeHtml(eid)}">
                                <span>${icon}</span>
                                <span style="overflow: hidden; text-overflow: ellipsis;">${escapeHtml(b.name)}</span>:
                                <strong>${isOn ? 'BẬT' : 'TẮT'}</strong>
                            </button>
                        `;
                    }).join('');

                    return `
                        <div class="panel-card" id="card_${escapeHtml(d.pairing_code)}">
                            <div class="card-top">
                                <div>
                                    <div class="card-room-name">${escapeHtml(d.room_name || 'Phòng Chưa Đặt Tên')}</div>
                                    <div class="card-floor-badge">${escapeHtml(d.floor || 'Tầng Trệt')} • Màn Hình Master</div>
                                </div>
                                <div style="display: flex; gap: 8px; align-items: center;">
                                    <span class="badge-fw-top" style="background: rgba(168, 85, 247, 0.2); color: #d8b4fe; font-size: 11px; font-weight: 700; font-family: 'JetBrains Mono', monospace; padding: 4px 9px; border-radius: 20px; border: 1px solid rgba(168, 85, 247, 0.4); display: flex; align-items: center; gap: 4px;">
                                        🚀 ${escapeHtml(d.firmware_version || 'v3.0.0')}
                                    </span>
                                    <div class="online-pill ${isOnline ? '' : 'offline'}">
                                        <span class="status-dot"></span>
                                        <span>${isOnline ? 'ONLINE' : 'OFFLINE'}</span>
                                    </div>
                                </div>
                            </div>

                            <div class="card-details">
                                <div class="card-detail-item"><span>Mã Ghép Nối:</span><span class="val" style="color: #38bdf8;">${escapeHtml(d.pairing_code)}</span></div>
                                <div class="card-detail-item"><span>Phiên Bản FW:</span><span class="val" style="color: #c084fc; font-weight: 700;">${escapeHtml(d.firmware_version || 'v3.0.0')}</span></div>
                                <div class="card-detail-item"><span>Kênh Đàm Thoại:</span><span class="val" style="color: #34d399; font-weight: 700;">ID: ${d.intercom_id || 1}</span></div>
                                <div class="card-detail-item"><span>Địa Chỉ MAC:</span><span class="val">${escapeHtml(d.mac)}</span></div>
                                <div class="card-detail-item"><span>IP Màn Hình:</span><span class="val">${escapeHtml(d.ip)}</span></div>
                                <div class="card-detail-item"><span>Model Phần Cứng:</span><span class="val">${escapeHtml(d.model || 'ES3C28P 2.8"')}</span></div>
                            </div>

                            <div class="card-entities">
                                <div class="entities-label-row">
                                    <span class="entities-label">Nút Bấm Điều Khiển Home Assistant:</span>
                                    <span class="entities-count-badge">${buttons.length} nút</span>
                                </div>
                                <div class="entity-toggle-grid">
                                    ${entityBtnsHtml.length > 0 ? entityBtnsHtml : '<div style="font-size: 12px; color: #64748b; font-style: italic;">Chưa có nút bấm nào. Hãy mở trình cài đặt để thêm nút.</div>'}
                                </div>
                            </div>

                            <div class="card-actions">
                                <button class="btn-wizard" onclick="openInstallerWizard('${escapeHtml(d.pairing_code)}')">
                                    🛠️ Trình Cài Đặt Nút Bấm
                                </button>
                                <button class="btn-intercom-card" onclick="openIntercomModalForTarget(${d.intercom_id || 1}, '${escapeHtml(d.room_name || d.pairing_code)}')">
                                    🎙️ Gọi Phòng Này
                                </button>
                                <button class="btn-sync-action" onclick="syncPanel('${escapeHtml(d.pairing_code)}')">
                                    🔄 Đồng Bộ
                                </button>
                                <button class="btn-ota-card" onclick="startSinglePanelOTA('${escapeHtml(d.pairing_code)}')">
                                    🚀 Cập Nhật OTA
                                </button>
                                <button class="btn-reset-wifi" onclick="resetWifiToAP('${escapeHtml(d.pairing_code)}')">
                                    ⚙️ Về AP (192.168.4.1)
                                </button>
                                <button class="btn-unpair" onclick="unpairPanel('${escapeHtml(d.pairing_code)}')">
                                    Hủy Ghép
                                </button>
                            </div>

                            <div class="ota-card-progress" id="cardOtaBox_${escapeHtml(d.pairing_code)}" style="display: none; margin-top: 12px; background: rgba(168, 85, 247, 0.1); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 8px; padding: 10px;">
                                <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 5px;">
                                    <span style="color: #c084fc; font-weight: 700;">🚀 NÂNG CẤP FIRMWARE OTA:</span>
                                    <span id="cardOtaPct_${escapeHtml(d.pairing_code)}" style="color: #fff; font-weight: 700;">0%</span>
                                </div>
                                <div style="background: #1e293b; border-radius: 9999px; height: 7px; overflow: hidden;">
                                    <div id="cardOtaFill_${escapeHtml(d.pairing_code)}" style="width: 0%; height: 100%; background: linear-gradient(90deg, #a855f7, #38bdf8); transition: width 0.2s;"></div>
                                </div>
                                <div id="cardOtaMsg_${escapeHtml(d.pairing_code)}" style="font-size: 10px; color: #94a3b8; margin-top: 5px;">Đang chuẩn bị...</div>
                            </div>
                        </div>
                    `;
                }).join('');
            }
        }

        function updateEntityButtons(entityId, state) {
            const isOn = state === 'on' || (state !== 'off' && state !== 'unavailable');
            const btns = document.querySelectorAll(`button[data-entity-id="${entityId}"]`);
            btns.forEach(btn => {
                const isLight = entityId.startsWith('light');
                const isFan = entityId.startsWith('fan');
                const isClimate = entityId.startsWith('climate');

                let baseClass = 'entity-btn';
                if (isLight && isOn) baseClass += ' on-light';
                else if (isFan && isOn) baseClass += ' on-fan';
                else if (isClimate && isOn) baseClass += ' on-climate';
                else if (isOn) baseClass += ' on-switch';

                btn.className = baseClass;
                const strong = btn.querySelector('strong');
                if (strong) strong.textContent = isOn ? 'BẬT' : 'TẮT';
            });
        }

        // -------------------------------------------------------------------------
        // 3. TRÌNH CÀI ĐẶT & THÊM NÚT BẤM (INSTALLER WIZARD)
        // -------------------------------------------------------------------------
        function switchWizardTab(tabId) {
            document.querySelectorAll('.wizard-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            const idx = tabId === 'tab_room' ? 0 : (tabId === 'tab_buttons' ? 1 : 2);
            document.querySelectorAll('.wizard-tab')[idx].classList.add('active');
            document.getElementById(tabId).classList.add('active');
        }

        // -------------------------------------------------------------------------
        // 3. CẤU HÌNH HOME ASSISTANT MODAL & TIỆN ÍCH AREA REGISTRY
        // -------------------------------------------------------------------------
        async function openHAConfigModal() {
            try {
                const res = await fetch('/api/ha/config');
                if (res.ok) {
                    const cfg = await res.json();
                    document.getElementById('haWsUrlInput').value = cfg.ha_ws_url || "";
                    document.getElementById('haTokenInput').value = "";
                    document.getElementById('haTokenInput').placeholder = cfg.ha_token_preview ? `Hiện tại: ${cfg.ha_token_preview} (để trống nếu không đổi)` : "Nhập token mới...";
                    
                    const badge = document.getElementById('haModalStatusBadge');
                    if (cfg.authenticated) {
                        badge.textContent = "Đã Kết Nối Thành Công";
                        badge.style.background = "rgba(16, 185, 129, 0.2)";
                        badge.style.color = "#34d399";
                    } else {
                        badge.textContent = "Chưa Xác Thực / Offline";
                        badge.style.background = "rgba(239, 68, 68, 0.2)";
                        badge.style.color = "#f87171";
                    }

                    document.getElementById('haModalFloorsCount').textContent = cfg.floors_count || 0;
                    document.getElementById('haModalAreasCount').textContent = cfg.areas_count || 0;
                    document.getElementById('haModalEntitiesCount').textContent = currentEntities.length || 0;
                }
            } catch (e) {
                console.error("Error fetching HA config:", e);
            }
            document.getElementById('haTestResultBanner').style.display = 'none';
            document.getElementById('haConfigModal').classList.add('active');
        }

        function closeHAConfigModal() {
            document.getElementById('haConfigModal').classList.remove('active');
        }

        function toggleTokenVisibility() {
            const input = document.getElementById('haTokenInput');
            input.type = input.type === 'password' ? 'text' : 'password';
        }

        async function testHAConnectionFromModal() {
            const url = document.getElementById('haWsUrlInput').value.trim();
            const token = document.getElementById('haTokenInput').value.trim();
            const banner = document.getElementById('haTestResultBanner');
            
            banner.style.display = 'block';
            banner.style.background = 'rgba(56, 189, 248, 0.15)';
            banner.style.border = '1px solid #38bdf8';
            banner.style.color = '#38bdf8';
            banner.innerHTML = '⏳ Đang thử kết nối WebSocket tới Home Assistant...';

            try {
                const res = await fetch('/api/ha/test_connection', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ha_ws_url: url, ha_token: token })
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    banner.style.background = 'rgba(16, 185, 129, 0.15)';
                    banner.style.border = '1px solid #10b981';
                    banner.style.color = '#34d399';
                    banner.innerHTML = `✓ Kết nối THÀNH CÔNG! Đã xác thực với HA.<br>• Tìm thấy <strong>${data.floors_found}</strong> tầng, <strong>${data.areas_found}</strong> phòng.`;
                } else {
                    banner.style.background = 'rgba(239, 68, 68, 0.15)';
                    banner.style.border = '1px solid #ef4444';
                    banner.style.color = '#f87171';
                    banner.innerHTML = `✕ Thử nghiệm thất bại: ${escapeHtml(data.message || 'Không thể xác thực')}`;
                }
            } catch (e) {
                banner.style.background = 'rgba(239, 68, 68, 0.15)';
                banner.style.border = '1px solid #ef4444';
                banner.style.color = '#f87171';
                banner.innerHTML = `✕ Lỗi mạng khi gọi kiểm tra: ${escapeHtml(e.message)}`;
            }
        }

        async function saveHAConfigFromModal() {
            const url = document.getElementById('haWsUrlInput').value.trim();
            const token = document.getElementById('haTokenInput').value.trim();
            if (!url) {
                alert("Vui lòng nhập Home Assistant WebSocket URL!");
                return;
            }

            try {
                const res = await fetch('/api/ha/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ha_ws_url: url, ha_token: token })
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    showToast("✓ Đã lưu cấu hình Home Assistant và kết nối lại!");
                    closeHAConfigModal();
                    loadHAAreasIntoSelect();
                    fetchInitialData();
                } else {
                    showToast(data.message || "Lỗi khi lưu cấu hình HA", true);
                }
            } catch (e) {
                showToast("Lỗi khi gửi cấu hình tới NAS Hub", true);
            }
        }

        let entitySearchQuery = '';

        function onEntitySearchInput(val) {
            entitySearchQuery = (val || '').trim().toLowerCase();
            populateHAEntityDropdown();
        }

        function clearEntitySearch() {
            entitySearchQuery = '';
            const inp = document.getElementById('wizEntitySearchInput');
            if (inp) inp.value = '';
            populateHAEntityDropdown();
        }

        function setupWizardFloorsAndAreas(selectedFloor, selectedRoomName) {
            // 1. Cập nhật danh sách Tầng từ Home Assistant (Pi 5)
            const floorSel = document.getElementById('wizFloorSelect');
            if (floorSel) {
                let floorHtml = '';
                const floors = haFloorsList.length > 0 ? haFloorsList : [
                    { floor_id: "tret", name: "tret", level: 0 },
                    { floor_id: "tang1", name: "tang1", level: 1 },
                    { floor_id: "tang2", name: "tang2", level: 2 },
                    { floor_id: "tang_3", name: "tang 3", level: 3 }
                ];

                const sortedFloors = [...floors].sort((a, b) => (a.level ?? 99) - (b.level ?? 99));
                sortedFloors.forEach(f => {
                    const flName = f.name || f.floor_id;
                    const levelLabel = f.level !== undefined ? ` (Cấp ${f.level})` : '';
                    floorHtml += `<option value="${escapeHtml(flName)}">🏢 ${escapeHtml(flName)}${levelLabel}</option>`;
                });
                floorSel.innerHTML = floorHtml;

                if (selectedFloor) {
                    let matched = false;
                    for (let i = 0; i < floorSel.options.length; i++) {
                        const optVal = floorSel.options[i].value;
                        if (optVal.toLowerCase() === selectedFloor.toLowerCase() ||
                            optVal.toLowerCase().includes(selectedFloor.toLowerCase()) ||
                            selectedFloor.toLowerCase().includes(optVal.toLowerCase())) {
                            floorSel.selectedIndex = i;
                            matched = true;
                            break;
                        }
                    }
                    if (!matched) {
                        floorSel.add(new Option(`🏢 ${selectedFloor}`, selectedFloor, true, true));
                    }
                }
            }

            // 2. Tự động nhận diện Area ID nếu tên phòng khớp với Home Assistant
            currentSelectedAreaId = "";
            if (selectedRoomName && haAreasList.length > 0) {
                const sRoom = selectedRoomName.trim().toLowerCase();
                const matchedArea = haAreasList.find(a => 
                    (a.name && a.name.toLowerCase() === sRoom) || 
                    (a.area_id && a.area_id.toLowerCase() === sRoom) ||
                    (a.name && sRoom.includes(a.name.toLowerCase())) ||
                    (a.name && a.name.toLowerCase().includes(sRoom))
                );
                if (matchedArea) {
                    currentSelectedAreaId = matchedArea.area_id;
                }
            }

            // 3. Đổ danh sách phòng theo tầng vào wizHaAreaSelect
            populateWizardAreaSelect(currentSelectedAreaId);
        }

        function populateWizardAreaSelect(selectedAreaId) {
            const areaSel = document.getElementById('wizHaAreaSelect');
            if (!areaSel) return;

            let html = '<option value="">-- Bấm để chọn phòng có sẵn trên Home Assistant (Pi 5) --</option>';
            const areasByFloor = {};
            const noFloorAreas = [];

            haAreasList.forEach(a => {
                const flName = a.floor_name || a.floor_id;
                if (flName) {
                    if (!areasByFloor[flName]) areasByFloor[flName] = [];
                    areasByFloor[flName].push(a);
                } else {
                    noFloorAreas.push(a);
                }
            });

            for (const [flName, areas] of Object.entries(areasByFloor)) {
                html += `<optgroup label="🏢 Tầng: ${escapeHtml(flName)}">`;
                areas.forEach(a => {
                    const sel = (selectedAreaId && a.area_id === selectedAreaId) ? 'selected' : '';
                    html += `<option value="${escapeHtml(a.area_id)}" data-name="${escapeHtml(a.name)}" data-floor="${escapeHtml(a.floor_name || a.floor_id || '')}" ${sel}>
                        🏠 ${escapeHtml(a.name)}
                    </option>`;
                });
                html += `</optgroup>`;
            }

            if (noFloorAreas.length > 0) {
                html += `<optgroup label="📍 Khu Vực Khác">`;
                noFloorAreas.forEach(a => {
                    const sel = (selectedAreaId && a.area_id === selectedAreaId) ? 'selected' : '';
                    html += `<option value="${escapeHtml(a.area_id)}" data-name="${escapeHtml(a.name)}" data-floor="" ${sel}>
                        🏠 ${escapeHtml(a.name)}
                    </option>`;
                });
                html += `</optgroup>`;
            }

            areaSel.innerHTML = html;
        }

        function onWizardFloorChanged() {
            updateScreenPreview();
            populateHAEntityDropdown();
        }

        function onWizardRoomNameChanged() {
            const roomName = (document.getElementById('wizRoomName')?.value || '').trim().toLowerCase();
            const matchedArea = haAreasList.find(a => 
                (a.name && a.name.toLowerCase() === roomName) || 
                (a.area_id && a.area_id.toLowerCase() === roomName)
            );
            if (matchedArea) {
                currentSelectedAreaId = matchedArea.area_id;
                const areaSel = document.getElementById('wizHaAreaSelect');
                if (areaSel) areaSel.value = matchedArea.area_id;
            }
            updateScreenPreview();
            populateHAEntityDropdown();
        }

        async function loadHAAreasIntoSelect() {
            try {
                const res = await fetch('/api/ha/areas');
                if (res.ok) {
                    const data = await res.json();
                    haAreasList = data.areas || [];
                    haFloorsList = data.floors || [];
                    const curFloor = document.getElementById('wizFloorSelect')?.value;
                    const curRoom = document.getElementById('wizRoomName')?.value;
                    setupWizardFloorsAndAreas(curFloor, curRoom);
                }
            } catch (e) {
                console.error("Error loading HA areas:", e);
            }
        }

        function onHaAreaSelectChanged() {
            const sel = document.getElementById('wizHaAreaSelect');
            const opt = sel.options[sel.selectedIndex];
            if (!opt || !sel.value) return;

            const areaId = sel.value;
            const areaName = opt.getAttribute('data-name');
            const floorName = opt.getAttribute('data-floor');
            currentSelectedAreaId = areaId;

            if (areaName) {
                document.getElementById('wizRoomName').value = areaName;
            }

            if (floorName) {
                const floorSel = document.getElementById('wizFloorSelect');
                let found = false;
                for (let i = 0; i < floorSel.options.length; i++) {
                    const optVal = floorSel.options[i].value;
                    if (optVal.toLowerCase() === floorName.toLowerCase() || 
                        optVal.toLowerCase().includes(floorName.toLowerCase()) ||
                        floorName.toLowerCase().includes(optVal.toLowerCase())) {
                        floorSel.selectedIndex = i;
                        found = true;
                        break;
                    }
                }
                if (!found && floorName) {
                    const newOpt = new Option(`🏢 ${floorName}`, floorName, true, true);
                    floorSel.add(newOpt);
                }
            }

            updateScreenPreview();
            populateHAEntityDropdown();
            showToast(`✓ Đã chọn phòng [${areaName}]${floorName ? ' - Tầng: ' + floorName : ''} từ Home Assistant`);
        }

        // -------------------------------------------------------------------------
        // 4. TRÌNH CÀI ĐẶT & THÊM NÚT BẤM (INSTALLER WIZARD)
        // -------------------------------------------------------------------------
        function switchWizardTab(tabId) {
            document.querySelectorAll('.wizard-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            const idx = tabId === 'tab_room' ? 0 : (tabId === 'tab_buttons' ? 1 : 2);
            document.querySelectorAll('.wizard-tab')[idx].classList.add('active');
            document.getElementById(tabId).classList.add('active');
        }

        function populateHAEntityDropdown() {
            const sel = document.getElementById('wizHaEntitySelect');
            if (!sel) return;

            const roomName = (document.getElementById('wizRoomName')?.value || '').trim().toLowerCase();
            const floorVal = (document.getElementById('wizFloorSelect')?.value || '').trim().toLowerCase();
            const activeAreaId = currentSelectedAreaId ? currentSelectedAreaId.toLowerCase() : '';

            // Lọc theo từ khóa tìm kiếm nếu có
            let filtered = currentEntities;
            if (entitySearchQuery) {
                filtered = currentEntities.filter(e => {
                    const eid = (e.entity_id || '').toLowerCase();
                    const name = (e.name || '').toLowerCase();
                    const area = (e.area_name || e.area_id || '').toLowerCase();
                    const fl = (e.floor_name || e.floor_id || '').toLowerCase();
                    return eid.includes(entitySearchQuery) || 
                           name.includes(entitySearchQuery) || 
                           area.includes(entitySearchQuery) || 
                           fl.includes(entitySearchQuery);
                });
            }

            const countBadge = document.getElementById('wizEntityMatchCount');
            if (countBadge) {
                countBadge.textContent = entitySearchQuery ? `(Tìm thấy ${filtered.length}/${currentEntities.length})` : `(${currentEntities.length} thực thể)`;
            }

            // Phân nhóm theo 4 cấp độ ưu tiên:
            // 1. Thuộc phòng hiện tại (Ưu tiên cao nhất ⭐)
            const roomEntities = [];
            // 2. Cùng tầng hiện tại (Ưu tiên nhì 🏢)
            const sameFloorEntities = [];
            // 3. Các phòng & tầng khác (📍)
            const otherRoomEntities = [];
            // 4. Thiết bị chung / chưa gán phòng (🌐)
            const unassignedEntities = [];

            filtered.forEach(e => {
                const eAreaId = (e.area_id || '').toLowerCase();
                const eAreaName = (e.area_name || '').toLowerCase();
                const eFloorName = (e.floor_name || '').toLowerCase();
                const eFloorId = (e.floor_id || '').toLowerCase();

                // 1. Kiểm tra thuộc phòng hiện tại
                const isCurrentRoom = (activeAreaId && eAreaId === activeAreaId) || 
                                     (roomName && (eAreaName === roomName || eAreaId === roomName || (eAreaName && roomName.includes(eAreaName)) || (eAreaId && roomName.includes(eAreaId))));

                if (isCurrentRoom) {
                    roomEntities.push(e);
                    return;
                }

                // 2. Kiểm tra cùng tầng hiện tại
                const isSameFloor = floorVal && (
                    (eFloorName && (eFloorName === floorVal || floorVal.includes(eFloorName) || eFloorName.includes(floorVal))) ||
                    (eFloorId && (eFloorId === floorVal || floorVal.includes(eFloorId) || eFloorId.includes(floorVal)))
                );

                if (isSameFloor) {
                    sameFloorEntities.push(e);
                    return;
                }

                // 3. Thiết bị thuộc phòng khác
                if (e.area_id || e.area_name) {
                    otherRoomEntities.push(e);
                } else {
                    unassignedEntities.push(e);
                }
            });

            // Sắp xếp theo domain rồi theo tên
            const sortEntities = (list) => {
                return list.sort((a, b) => {
                    const domA = a.domain || '';
                    const domB = b.domain || '';
                    if (domA !== domB) return domA.localeCompare(domB);
                    return (a.name || a.entity_id).localeCompare(b.name || b.entity_id, 'vi');
                });
            };

            sortEntities(roomEntities);
            sortEntities(sameFloorEntities);
            
            otherRoomEntities.sort((a, b) => {
                const flA = a.floor_name || a.floor_id || 'zzz';
                const flB = b.floor_name || b.floor_id || 'zzz';
                if (flA !== flB) return flA.localeCompare(flB, 'vi');
                const arA = a.area_name || a.area_id || 'zzz';
                const arB = b.area_name || b.area_id || 'zzz';
                if (arA !== arB) return arA.localeCompare(arB, 'vi');
                return (a.name || a.entity_id).localeCompare(b.name || b.entity_id, 'vi');
            });

            sortEntities(unassignedEntities);

            let html = '<option value="">-- Bấm chọn thực thể để thêm nút bấm điều khiển --</option>';

            const currentRoomDisplayName = document.getElementById('wizRoomName')?.value?.trim() || 'Phòng Hiện Tại';
            const currentFloorDisplayName = document.getElementById('wizFloorSelect')?.value || 'Tầng Hiện Tại';

            if (roomEntities.length > 0) {
                html += `<optgroup label="⭐ THUỘC PHÒNG NÀY: [${escapeHtml(currentRoomDisplayName)}] (${roomEntities.length} thiết bị)">`;
                roomEntities.forEach(e => {
                    html += `<option value="${escapeHtml(e.entity_id)}" data-name="${escapeHtml(e.name || '')}" data-domain="${escapeHtml(e.domain || '')}">
                        ⭐ ${getIconForDomain(e.domain)} ${escapeHtml(e.name || e.entity_id)} (${escapeHtml(e.entity_id)})
                    </option>`;
                });
                html += `</optgroup>`;
            }

            if (sameFloorEntities.length > 0) {
                html += `<optgroup label="🏢 CÙNG TẦNG: [${escapeHtml(currentFloorDisplayName)}] (${sameFloorEntities.length} thiết bị)">`;
                sameFloorEntities.forEach(e => {
                    const roomTag = e.area_name ? `[${e.area_name}] ` : '';
                    html += `<option value="${escapeHtml(e.entity_id)}" data-name="${escapeHtml(e.name || '')}" data-domain="${escapeHtml(e.domain || '')}">
                        🏢 ${escapeHtml(roomTag)}${getIconForDomain(e.domain)} ${escapeHtml(e.name || e.entity_id)} (${escapeHtml(e.entity_id)})
                    </option>`;
                });
                html += `</optgroup>`;
            }

            if (otherRoomEntities.length > 0) {
                html += `<optgroup label="📍 CÁC TẦNG & PHÒNG KHÁC (${otherRoomEntities.length} thiết bị)">`;
                otherRoomEntities.forEach(e => {
                    const locationTag = (e.floor_name ? `[${e.floor_name}] ` : '') + (e.area_name ? `${e.area_name}: ` : '');
                    html += `<option value="${escapeHtml(e.entity_id)}" data-name="${escapeHtml(e.name || '')}" data-domain="${escapeHtml(e.domain || '')}">
                        📍 ${escapeHtml(locationTag)}${getIconForDomain(e.domain)} ${escapeHtml(e.name || e.entity_id)} (${escapeHtml(e.entity_id)})
                    </option>`;
                });
                html += `</optgroup>`;
            }

            if (unassignedEntities.length > 0) {
                html += `<optgroup label="🌐 TOÀN BỘ NHÀ / THIẾT BỊ KHÁC (${unassignedEntities.length} thiết bị)">`;
                unassignedEntities.forEach(e => {
                    html += `<option value="${escapeHtml(e.entity_id)}" data-name="${escapeHtml(e.name || '')}" data-domain="${escapeHtml(e.domain || '')}">
                        🌐 ${getIconForDomain(e.domain)} ${escapeHtml(e.name || e.entity_id)} (${escapeHtml(e.entity_id)})
                    </option>`;
                });
                html += `</optgroup>`;
            }

            if (filtered.length === 0) {
                html += `<option value="" disabled>Không tìm thấy thực thể nào khớp với "${escapeHtml(entitySearchQuery)}"</option>`;
            }

            sel.innerHTML = html;
        }

        function onSelectHAEntity(val) {
            if (!val) return;
            const sel = document.getElementById('wizHaEntitySelect');
            const opt = sel.options[sel.selectedIndex];
            const name = opt.getAttribute('data-name') || val.split('.')[1] || val;
            const domain = opt.getAttribute('data-domain') || val.split('.')[0] || 'light';

            document.getElementById('wizCustomEntityId').value = val;
            document.getElementById('wizCustomButtonName').value = name;
            document.getElementById('wizIconSelect').value = domain;
        }

        function openInstallerWizard(code) {
            const dev = currentDevices.find(d => d.pairing_code === code) || {};
            activeWizardDevice = dev;
            currentSelectedAreaId = "";

            document.getElementById('modalCodeBadge').textContent = `${code} • FW: ${dev.firmware_version || 'v3.0.0'}`;
            document.getElementById('wizPairingCode').value = code;
            document.getElementById('wizRoomName').value = dev.room_name || "Phòng Khách Master";

            // Xóa bộ lọc tìm kiếm cũ
            clearEntitySearch();

            // Khởi tạo tầng & phòng lấy từ Home Assistant
            setupWizardFloorsAndAreas(dev.floor || "tret", dev.room_name || "Phòng khách trệt");
            loadHAAreasIntoSelect(); // đồng bộ ngầm nếu HA có cập nhật mới

            // Load buttons
            wizardButtons = [];
            if (dev.buttons && dev.buttons.length > 0) {
                wizardButtons = JSON.parse(JSON.stringify(dev.buttons));
            } else if (dev.entities && dev.entities.length > 0) {
                wizardButtons = dev.entities.map((eid, idx) => ({
                    id: `btn_${idx+1}`,
                    name: eid.split('.')[1].replace('_', ' ').toUpperCase(),
                    entity_id: eid,
                    icon: eid.split('.')[0],
                    domain: eid.split('.')[0]
                }));
            } else {
                wizardButtons = [
                    { id: "btn_1", name: "Đèn Chính", entity_id: "light.moes_matter_switch_den_3_6", icon: "light" },
                    { id: "btn_2", name: "Máy Lạnh", entity_id: "climate.151732606266034_climate", icon: "climate" }
                ];
            }

            // Load settings
            const settings = dev.settings || { brightness: 90, volume: 80, mic_gain: 5, ring_on_call: true, ai_model: "gemini" };
            document.getElementById('wizBrightness').value = settings.brightness || 90;
            document.getElementById('brightValLabel').textContent = (settings.brightness || 90) + '%';
            document.getElementById('wizVolume').value = settings.volume || 80;
            document.getElementById('volumeValLabel').textContent = (settings.volume || 80) + '%';
            const micGain = settings.mic_gain || 5;
            document.getElementById('wizMicGain').value = micGain;
            updateMicGainLabel(micGain);
            document.getElementById('wizRingOnCall').checked = (settings.ring_on_call !== undefined) ? !!settings.ring_on_call : true;
            document.getElementById('wizAiModel').value = settings.ai_model || 'gemini';

            renderWizardButtonsList();
            updateScreenPreview();
            populateHAEntityDropdown();
            switchWizardTab('tab_room');

            document.getElementById('installerModal').classList.add('active');
        }

        function closeInstallerModal() {
            document.getElementById('installerModal').classList.remove('active');
        }

        function renderWizardButtonsList() {
            document.getElementById('wizBtnCount').textContent = wizardButtons.length;
            const container = document.getElementById('wizButtonsList');
            if (wizardButtons.length === 0) {
                container.innerHTML = `<div style="grid-column: 1 / -1; font-size: 12px; color: #94a3b8; font-style: italic; padding: 8px;">Chưa có nút bấm nào. Hãy điền form bên dưới để thêm nút điều khiển.</div>`;
            } else {
                container.innerHTML = wizardButtons.map((b, idx) => `
                    <div class="button-item-card">
                        <div style="font-size: 20px;">${getIconForDomain(b.icon)}</div>
                        <div class="button-item-info">
                            <span class="name">${escapeHtml(b.name)}</span>
                            <span class="eid">${escapeHtml(b.entity_id)}</span>
                        </div>
                        <button class="btn-del-item" onclick="removeButtonFromWizard(${idx})" title="Xóa nút này">✕</button>
                    </div>
                `).join('');
            }
            updateScreenPreview();
        }

        function addNewButtonToPanel() {
            const eid = document.getElementById('wizCustomEntityId').value.trim();
            const name = document.getElementById('wizCustomButtonName').value.trim();
            const icon = document.getElementById('wizIconSelect').value;

            if (!eid) {
                alert("Vui lòng nhập hoặc chọn Entity ID từ Home Assistant!");
                return;
            }
            if (!name) {
                alert("Vui lòng nhập tên hiển thị cho nút bấm!");
                return;
            }

            wizardButtons.push({
                id: `btn_${Date.now()}`,
                name: name,
                entity_id: eid,
                icon: icon,
                domain: eid.split('.')[0]
            });

            // Reset inputs
            document.getElementById('wizCustomEntityId').value = "";
            document.getElementById('wizCustomButtonName').value = "";
            document.getElementById('wizHaEntitySelect').value = "";

            renderWizardButtonsList();
            showToast(`✓ Đã thêm nút [${name}]`);
        }

        function removeButtonFromWizard(idx) {
            const removed = wizardButtons.splice(idx, 1);
            renderWizardButtonsList();
            if (removed.length > 0) {
                showToast(`Đã xóa nút [${removed[0].name}]`);
            }
        }

        function updateScreenPreview() {
            const room = document.getElementById('wizRoomName').value.trim() || "Phòng Khách";
            document.getElementById('mockHeaderTitle').textContent = `NALA: ${room}`;

            const grid = document.getElementById('mockButtonsGrid');
            if (wizardButtons.length === 0) {
                grid.innerHTML = `<div class="screen-mock-btn" style="grid-column: 1 / -1; color: #64748b;">(Chưa có nút)</div>`;
            } else {
                grid.innerHTML = wizardButtons.slice(0, 6).map(b => `
                    <div class="screen-mock-btn">
                        ${getIconForDomain(b.icon)} ${escapeHtml(b.name)}
                    </div>
                `).join('');
            }
        }

        function updateMicGainLabel(val) {
            const v = parseInt(val) || 5;
            const dbs = ["", "+6dB", "+12dB", "+18dB", "+24dB", "+30dB", "+36dB", "+42dB"];
            const desc = ["", "Thấp", "Vừa", "Chuẩn", "Nhạy", "Rất nhạy", "Cực nhạy", "Tối đa"];
            const text = `Cấp ${v} (${dbs[v] || '+30dB'} - ${desc[v] || ''})`;
            const el = document.getElementById('micGainValLabel');
            if (el) el.textContent = text;
        }

        async function saveInstallerConfig() {
            const code = document.getElementById('wizPairingCode').value;
            const room = document.getElementById('wizRoomName').value.trim() || "Phòng Khách";
            const floor = document.getElementById('wizFloorSelect').value;

            const brightness = parseInt(document.getElementById('wizBrightness').value) || 90;
            const volume = parseInt(document.getElementById('wizVolume').value) || 80;
            const mic_gain = parseInt(document.getElementById('wizMicGain').value) || 5;
            const ring_on_call = document.getElementById('wizRingOnCall').checked;
            const ai_model = document.getElementById('wizAiModel').value;

            const payload = {
                pairing_code: code,
                room_name: room,
                floor: floor,
                buttons: wizardButtons,
                entities: wizardButtons.map(b => b.entity_id),
                settings: {
                    brightness: brightness,
                    volume: volume,
                    mic_gain: mic_gain,
                    ring_on_call: ring_on_call,
                    ai_model: ai_model
                }
            };

            try {
                const res = await fetch('/api/devices/pair', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    showToast(`✓ Đã lưu & đồng bộ tức thời xuống Panel [${code}]!`);
                    closeInstallerModal();
                } else {
                    showToast('Lỗi khi lưu cấu hình', true);
                }
            } catch (e) {
                console.error("Save error:", e);
                showToast('Lỗi kết nối máy chủ', true);
            }
        }

        async function syncPanel(code) {
            try {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: "admin_action",
                        action: "sync_panel",
                        pairing_code: code
                    }));
                }

                const res = await fetch('/api/devices/action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pairing_code: code, action: 'sync' })
                });

                if (res.ok) {
                    showToast(`✓ Đã đẩy lệnh đồng bộ ngay xuống Panel [${code}]!`);
                } else {
                    showToast(`Không thể đồng bộ: Panel [${code}] có thể đang offline`, true);
                }
            } catch (e) {
                console.error("Sync error:", e);
                showToast('Lỗi gửi lệnh đồng bộ', true);
            }
        }

        async function resetWifiToAP(code) {
            if (!confirm(`Bạn có chắc chắn muốn chuyển màn hình [${code}] về Chế Độ Cấu Hình WiFi Soft-AP (192.168.4.1)?\n\nMàn hình sẽ xóa WiFi cũ và phát lại mạng NALA_PANEL_${code}.`)) {
                return;
            }
            try {
                const res = await fetch('/api/devices/action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pairing_code: code, action: 'enter_ap' })
                });
                if (res.ok) {
                    showToast(`⚙️ Đã chuyển màn hình [${code}] về Soft-AP 192.168.4.1!`);
                } else {
                    showToast('Lỗi gửi lệnh chuyển AP', true);
                }
            } catch (e) {
                console.error("Enter AP error:", e);
                showToast('Lỗi gửi lệnh chuyển AP', true);
            }
        }

        async function unpairPanel(code) {
            if (!confirm(`Bạn có chắc chắn muốn hủy ghép nối màn hình [${code}]? Màn hình sẽ quay về trạng thái Chờ ghép nối.`)) {
                return;
            }
            try {
                const res = await fetch('/api/devices/unpair', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pairing_code: code })
                });
                if (res.ok) {
                    showToast(`✓ Đã hủy ghép nối màn hình [${code}]`);
                }
            } catch (e) {
                console.error("Unpair error:", e);
            }
        }

        async function toggleEntity(entityId) {
            const cur = entityStates[entityId] || 'off';
            const next = cur === 'on' ? 'off' : 'on';
            entityStates[entityId] = next;
            updateEntityButtons(entityId, next);

            // Gửi qua WebSocket
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: "ha_action",
                    payload: {
                        domain: entityId.split('.')[0] || 'light',
                        service: 'toggle',
                        entity_id: entityId
                    }
                }));
            }

            // Đồng thời gọi REST API
            try {
                await fetch('/api/ha/call_service', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ entity_id: entityId, service: 'toggle' })
                });
            } catch (e) {
                console.error("Toggle error:", e);
            }
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        // -------------------------------------------------------------------------
        // 4. OTA FIRMWARE REALTIME MANAGEMENT & PROGRESS
        // -------------------------------------------------------------------------
        async function openOTAManagerModal() {
            await loadOtaStatus();
            renderOtaTrackerList();
            document.getElementById('otaManagerModal').classList.add('active');
        }

        function closeOTAManagerModal() {
            document.getElementById('otaManagerModal').classList.remove('active');
        }

        async function loadOtaStatus() {
            try {
                const res = await fetch('/api/ota/status');
                const badge = document.getElementById('otaMetaStatusBadge');
                const details = document.getElementById('otaMetaDetails');
                if (res.ok) {
                    const data = await res.json();
                    if (data.available) {
                        badge.textContent = "Sẵn Sàng OTA";
                        badge.style.background = "rgba(16, 185, 129, 0.2)";
                        badge.style.color = "#34d399";
                        details.innerHTML = `
                            • File: <strong style="color: #fff;">${escapeHtml(data.original_filename || data.latest_file)}</strong> (${data.size_mb} MB)<br>
                            • Phiên bản: <strong style="color: #c084fc;">${escapeHtml(data.version || 'v2.5.0')}</strong> &nbsp;|&nbsp; MD5: <code>${escapeHtml(data.md5 || '')}</code><br>
                            • Thời gian tải lên: <span style="color: #94a3b8;">${escapeHtml(data.upload_time || '')}</span><br>
                            • URL tải trực tiếp: <a href="${escapeHtml(data.download_url)}" target="_blank" style="color: #38bdf8; text-decoration: underline;">${escapeHtml(data.download_url)}</a>
                        `;
                    } else {
                        badge.textContent = "Chưa Có Firmware";
                        badge.style.background = "rgba(239, 68, 68, 0.2)";
                        badge.style.color = "#f87171";
                        details.innerHTML = `Chưa có bản firmware nào trên máy chủ NAS Hub. Vui lòng chọn file .bin ở trên và bấm "TẢI LÊN NAS HUB".`;
                    }
                }
            } catch (e) {
                console.error("Error loading OTA status:", e);
            }
        }

        async function uploadFirmwareFile() {
            const fileInput = document.getElementById('otaFileInput');
            const versionInput = document.getElementById('otaVersionInput');
            const progressText = document.getElementById('otaUploadProgressText');

            if (!fileInput.files || fileInput.files.length === 0) {
                alert("Vui lòng chọn file firmware (.bin) đã biên dịch từ PlatformIO!");
                return;
            }

            const file = fileInput.files[0];
            if (!file.name.endsWith('.bin')) {
                alert("File phải có định dạng đuôi là .bin!");
                return;
            }

            const ver = versionInput.value.trim() || 'v2.5.0';
            progressText.style.display = 'block';
            progressText.style.color = '#38bdf8';
            progressText.textContent = `⏳ Đang truyền file [${file.name}] (${(file.size / (1024*1024)).toFixed(2)} MB)...`;

            try {
                const uploadUrl = `/api/ota/upload?filename=${encodeURIComponent(file.name)}&version=${encodeURIComponent(ver)}`;
                const res = await fetch(uploadUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/octet-stream',
                        'X-Filename': file.name,
                        'X-Version': ver
                    },
                    body: file
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    progressText.style.color = '#34d399';
                    progressText.textContent = `✓ ${data.message}`;
                    showToast(data.message);
                    loadOtaStatus();
                    fileInput.value = '';
                } else {
                    progressText.style.color = '#f87171';
                    progressText.textContent = `✕ Lỗi: ${data.message || 'Không thể tải lên'}`;
                    showToast(data.message || "Lỗi tải lên", true);
                }
            } catch (e) {
                progressText.style.color = '#f87171';
                progressText.textContent = `✕ Lỗi mạng: ${e.message}`;
                showToast("Lỗi kết nối khi tải file", true);
            }
        }

        async function startBroadcastOTA() {
            if (!confirm("⚠️ CẢNH BÁO QUAN TRỌNG:\n\nBạn có chắc chắn muốn phát lệnh NÂNG CẤP FIRMWARE OTA tới TOÀN BỘ màn hình đang Online?\n\nCác màn hình sẽ tải firmware, nạp flash và tự khởi động lại.")) {
                return;
            }
            try {
                const res = await fetch('/api/ota/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target: "all" })
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    showToast(`🚀 ${data.message}`);
                } else {
                    showToast(data.message || "Lỗi phát lệnh OTA", true);
                }
            } catch (e) {
                showToast("Lỗi gửi lệnh OTA", true);
            }
        }

        async function startSinglePanelOTA(code) {
            if (!confirm(`Bạn có chắc chắn muốn NÂNG CẤP FIRMWARE OTA cho màn hình [${code}]?\n\nMàn hình sẽ tải file firmware mới từ NAS Hub và tự khởi động lại sau khi nạp xong.`)) {
                return;
            }
            try {
                const res = await fetch('/api/ota/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target: code })
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    showToast(`🚀 ${data.message}`);
                    const box = document.getElementById(`cardOtaBox_${code}`);
                    if (box) {
                        box.style.display = 'block';
                        document.getElementById(`cardOtaPct_${code}`).textContent = '0%';
                        document.getElementById(`cardOtaFill_${code}`).style.width = '0%';
                        document.getElementById(`cardOtaMsg_${code}`).textContent = 'Đã gửi lệnh OTA, chờ màn hình kết nối tải file...';
                    }
                } else {
                    showToast(data.message || "Lỗi phát lệnh OTA", true);
                }
            } catch (e) {
                showToast("Lỗi gửi lệnh OTA", true);
            }
        }

        function handleOtaProgress(data) {
            const code = data.pairing_code;
            if (!code) return;
            const pct = data.progress || 0;
            const status = data.status || 'progress';
            const msg = data.message || `Đang tải firmware: ${pct}%`;

            activeOtaPanels[code] = { progress: pct, status: status, message: msg };

            // 1. Update Card on main dashboard
            const box = document.getElementById(`cardOtaBox_${code}`);
            const fill = document.getElementById(`cardOtaFill_${code}`);
            const pctLabel = document.getElementById(`cardOtaPct_${code}`);
            const msgLabel = document.getElementById(`cardOtaMsg_${code}`);

            if (box) {
                box.style.display = 'block';
                if (fill) fill.style.width = `${pct}%`;
                if (pctLabel) pctLabel.textContent = `${pct}%`;
                if (msgLabel) msgLabel.textContent = msg;

                if (pct >= 100 || status === 'success') {
                    if (fill) fill.style.background = '#10b981';
                    if (msgLabel) msgLabel.innerHTML = '✓ Nạp Flash thành công! Đang khởi động lại...';
                    setTimeout(() => {
                        if (box) box.style.display = 'none';
                        delete activeOtaPanels[code];
                        renderOtaTrackerList();
                    }, 8000);
                } else if (status === 'error') {
                    if (fill) fill.style.background = '#ef4444';
                    if (msgLabel) msgLabel.innerHTML = `✕ Lỗi: ${escapeHtml(msg)}`;
                }
            }

            // 2. Update list in OTA Modal
            renderOtaTrackerList();
        }

        function renderOtaTrackerList() {
            const list = document.getElementById('otaTrackerList');
            if (!list) return;
            const keys = Object.keys(activeOtaPanels);
            if (keys.length === 0) {
                list.innerHTML = `<div style="font-size: 12px; color: #64748b; font-style: italic;">Chưa có tác vụ OTA nào đang chạy.</div>`;
                return;
            }

            list.innerHTML = keys.map(code => {
                const info = activeOtaPanels[code];
                const isSuccess = info.progress >= 100 || info.status === 'success';
                const isError = info.status === 'error';
                const color = isSuccess ? '#10b981' : (isError ? '#ef4444' : '#a855f7');

                return `
                    <div style="background: #0f172a; border: 1px solid var(--border-color); border-radius: 8px; padding: 10px;">
                        <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
                            <span style="font-weight: 700; color: #fff;">Màn Hình [${escapeHtml(code)}]</span>
                            <span style="font-weight: 700; color: ${color};">${info.progress}%</span>
                        </div>
                        <div style="background: #1e293b; border-radius: 9999px; height: 6px; overflow: hidden; margin-bottom: 4px;">
                            <div style="width: ${info.progress}%; height: 100%; background: ${color}; transition: width 0.2s;"></div>
                        </div>
                        <div style="font-size: 11px; color: #94a3b8;">${escapeHtml(info.message || info.status)}</div>
                    </div>
                `;
            }).join('');
        }

        // -------------------------------------------------------------------------
        // 5. INTERCOM REALTIME AUDIO (WEB PTT & REALTIME PLAYBACK)
        // -------------------------------------------------------------------------
        let currentIntercomTargets = [];
        let selectedIntercomTargetId = 255; // 0xFF: Toàn nhà
        let audioCtx = null;
        let isSpeakerEnabled = false;
        let nextPlayTime = 0;
        let mediaStream = null;
        let micSource = null;
        let scriptNode = null;
        let isWebPttActive = false;
        let webPttSeq = 0;

        function openIntercomModal() {
            renderIntercomTargets();
            document.getElementById('intercomModal').classList.add('active');
            attachPttEvents();
        }

        function openIntercomModalForTarget(targetId, targetName) {
            selectedIntercomTargetId = targetId;
            openIntercomModal();
            selectIntercomTarget(targetId);
        }

        function closeIntercomModal() {
            stopWebPtt();
            document.getElementById('intercomModal').classList.remove('active');
        }

        function selectIntercomTarget(targetId) {
            selectedIntercomTargetId = targetId;
            const buttons = document.querySelectorAll('.intercom-chan-btn');
            buttons.forEach(btn => {
                const bTarget = parseInt(btn.getAttribute('data-target'), 10);
                if (bTarget === targetId) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
        }

        function renderIntercomTargets() {
            const grid = document.getElementById('intercomTargetsGrid');
            if (!grid) return;

            let html = `
                <button class="intercom-chan-btn ${selectedIntercomTargetId === 255 ? 'active' : ''}" data-target="255" onclick="selectIntercomTarget(255)">
                    <span style="font-size: 20px;">📢</span>
                    <span>Toàn Nhà</span>
                    <span style="font-size: 10px; color: #34d399;">(Broadcast 0xFF)</span>
                </button>
            `;

            const targets = currentIntercomTargets.length > 0 ? currentIntercomTargets : currentDevices.map(d => ({
                id: d.intercom_id || 1,
                name: d.room_name || `Màn hình [${d.pairing_code}]`,
                floor: d.floor || '',
                code: d.pairing_code,
                online: d.online
            }));

            targets.forEach(t => {
                const isActive = selectedIntercomTargetId === t.id;
                const onlineDot = t.online ? '🟢' : '⚪';
                html += `
                    <button class="intercom-chan-btn ${isActive ? 'active' : ''}" data-target="${t.id}" onclick="selectIntercomTarget(${t.id})">
                        <span style="font-size: 20px;">📺</span>
                        <span style="overflow: hidden; text-overflow: ellipsis; max-width: 110px; white-space: nowrap;">${escapeHtml(t.name)}</span>
                        <span style="font-size: 10px; color: #94a3b8;">${onlineDot} Kênh ID: ${t.id}</span>
                    </button>
                `;
            });

            grid.innerHTML = html;
        }

        function initAudioContext() {
            if (!audioCtx) {
                const AudioContextClass = window.AudioContext || window.webkitAudioContext;
                audioCtx = new AudioContextClass({ sampleRate: 16000 });
            }
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
        }

        function toggleWebSpeaker() {
            initAudioContext();
            isSpeakerEnabled = !isSpeakerEnabled;
            const btn = document.getElementById('btnToggleWebSpeaker');
            const badge = document.getElementById('speakerLiveBadge');
            if (isSpeakerEnabled) {
                btn.textContent = '🔇 Tắt Loa Nghe';
                btn.style.background = '#ef4444';
                badge.textContent = 'Đang bật';
                badge.style.background = 'rgba(16, 185, 129, 0.2)';
                badge.style.color = '#34d399';
                showToast('Đã bật loa nghe đàm thoại thời gian thực');
            } else {
                btn.textContent = '🔊 Bật Loa Nghe';
                btn.style.background = '#10b981';
                badge.textContent = 'Đang tắt';
                badge.style.background = '#334155';
                badge.style.color = '#94a3b8';
                showToast('Đã tắt loa nghe đàm thoại');
            }
        }

        function playIntercomPcmChunk(pcmDataInt16) {
            if (!isSpeakerEnabled || !audioCtx) return;
            try {
                const floatData = new Float32Array(pcmDataInt16.length);
                for (let i = 0; i < pcmDataInt16.length; i++) {
                    floatData[i] = pcmDataInt16[i] / 32768.0;
                }
                const audioBuffer = audioCtx.createBuffer(1, floatData.length, 16000);
                audioBuffer.copyToChannel(floatData, 0);

                const source = audioCtx.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioCtx.destination);

                const currentTime = audioCtx.currentTime;
                if (nextPlayTime < currentTime) {
                    nextPlayTime = currentTime + 0.02;
                }
                source.start(nextPlayTime);
                nextPlayTime += audioBuffer.duration;
            } catch (e) {
                console.error('Lỗi phát âm thanh đàm thoại:', e);
            }
        }

        function handleIncomingBinaryPacket(buffer) {
            if (buffer.byteLength !== 520) return;
            const view = new DataView(buffer);
            const magic = view.getUint16(0, true);
            if (magic !== 0xA55A) return;

            const senderId = view.getUint8(2);
            const targetId = view.getUint8(3);
            const flag = view.getUint8(6);

            const pcm = new Int16Array(256);
            for (let i = 0; i < 256; i++) {
                pcm[i] = view.getInt16(7 + (i * 2), true);
            }
            playIntercomPcmChunk(pcm);
        }

        let pttEventsAttached = false;
        function attachPttEvents() {
            if (pttEventsAttached) return;
            const btn = document.getElementById('btnWebPtt');
            if (!btn) return;
            pttEventsAttached = true;

            const onDown = (e) => { e.preventDefault(); startWebPtt(); };
            const onUp = (e) => { e.preventDefault(); stopWebPtt(); };

            btn.addEventListener('mousedown', onDown);
            btn.addEventListener('mouseup', onUp);
            btn.addEventListener('mouseleave', onUp);

            btn.addEventListener('touchstart', onDown, { passive: false });
            btn.addEventListener('touchend', onUp, { passive: false });
            btn.addEventListener('touchcancel', onUp, { passive: false });
        }

        async function startWebPtt() {
            if (isWebPttActive) return;
            initAudioContext();
            try {
                mediaStream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        sampleRate: 16000,
                        channelCount: 1,
                        echoCancellation: true,
                        noiseSuppression: true
                    }
                });

                micSource = audioCtx.createMediaStreamSource(mediaStream);
                scriptNode = audioCtx.createScriptProcessor(256, 1, 1);

                isWebPttActive = true;
                webPttSeq = 0;

                const btn = document.getElementById('btnWebPtt');
                btn.style.background = 'radial-gradient(circle, #ef4444 0%, #b91c1c 100%)';
                btn.style.borderColor = '#f87171';
                btn.style.boxShadow = '0 0 35px rgba(239, 68, 68, 0.7)';
                document.getElementById('pttStatusLabel').innerHTML = '🔴 <span style="color: #ef4444; font-weight: 700;">ĐANG NÓI... NHẢ ĐỂ KẾT THÚC</span>';

                let isFirstFrame = true;

                scriptNode.onaudioprocess = (e) => {
                    if (!isWebPttActive || !ws || ws.readyState !== WebSocket.OPEN) return;
                    const inputData = e.inputBuffer.getChannelData(0);

                    const buffer = new ArrayBuffer(520);
                    const view = new DataView(buffer);
                    const u8 = new Uint8Array(buffer);

                    view.setUint16(0, 0xA55A, true);
                    view.setUint8(2, 0xFE); // sender: 0xFE (Web Admin)
                    view.setUint8(3, selectedIntercomTargetId);
                    view.setUint16(4, webPttSeq++, true);
                    view.setUint8(6, isFirstFrame ? 0x01 : 0x02);
                    isFirstFrame = false;

                    for (let i = 0; i < 256; i++) {
                        let s = Math.max(-1, Math.min(1, inputData[i] || 0));
                        let val = s < 0 ? s * 0x8000 : s * 0x7FFF;
                        view.setInt16(7 + (i * 2), val, true);
                    }

                    let crc = 0;
                    for (let i = 0; i < 519; i++) {
                        crc ^= u8[i];
                        for (let b = 0; b < 8; b++) {
                            crc = (crc & 0x80) ? ((crc << 1) ^ 0x07) : (crc << 1);
                        }
                    }
                    view.setUint8(519, crc & 0xFF);

                    ws.send(buffer);
                };

                micSource.connect(scriptNode);
                scriptNode.connect(audioCtx.destination);
            } catch (err) {
                console.error("Không thể mở Micro:", err);
                showToast("Lỗi: Không được phép truy cập Micro!", true);
                stopWebPtt();
            }
        }

        function stopWebPtt() {
            if (!isWebPttActive) return;
            isWebPttActive = false;

            if (ws && ws.readyState === WebSocket.OPEN) {
                const buffer = new ArrayBuffer(520);
                const view = new DataView(buffer);
                const u8 = new Uint8Array(buffer);
                view.setUint16(0, 0xA55A, true);
                view.setUint8(2, 0xFE);
                view.setUint8(3, selectedIntercomTargetId);
                view.setUint16(4, webPttSeq++, true);
                view.setUint8(6, 0x03); // STREAM_FLAG_END
                let crc = 0;
                for (let i = 0; i < 519; i++) {
                    crc ^= u8[i];
                    for (let b = 0; b < 8; b++) crc = (crc & 0x80) ? ((crc << 1) ^ 0x07) : (crc << 1);
                }
                view.setUint8(519, crc & 0xFF);
                ws.send(buffer);
            }

            if (scriptNode) { scriptNode.disconnect(); scriptNode = null; }
            if (micSource) { micSource.disconnect(); micSource = null; }
            if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null; }

            const btn = document.getElementById('btnWebPtt');
            if (btn) {
                btn.style.background = 'radial-gradient(circle, #059669 0%, #047857 100%)';
                btn.style.borderColor = '#10b981';
                btn.style.boxShadow = '0 0 25px rgba(16, 185, 129, 0.4)';
            }
            const lbl = document.getElementById('pttStatusLabel');
            if (lbl) lbl.innerHTML = 'Chạm hoặc giữ chuột để đàm thoại';
        }

        // -------------------------------------------------------------------------
        // 6. VOICE & INTERCOM HISTORY & SCHEDULED RETENTION
        // -------------------------------------------------------------------------
        let isHistoryModalOpen = false;
        let currentHistoryFilter = '';
        let currentHistoryRecords = [];

        async function openHistoryModal() {
            isHistoryModalOpen = true;
            document.getElementById('historyModal').classList.add('active');
            await loadHistorySettings();
            await loadHistoryData();
        }

        function closeHistoryModal() {
            isHistoryModalOpen = false;
            document.getElementById('historyModal').classList.remove('active');
        }

        function setHistoryFilter(filter) {
            currentHistoryFilter = filter;
            document.querySelectorAll('.hist-filter-btn').forEach(b => b.classList.remove('active'));
            if (filter === '') document.getElementById('filterAll').classList.add('active');
            else if (filter === 'voice_ai') document.getElementById('filterAI').classList.add('active');
            else if (filter === 'intercom') document.getElementById('filterIntercom').classList.add('active');
            renderHistoryList();
        }

        async function loadHistorySettings() {
            try {
                const res = await fetch('/api/history/settings');
                if (res.ok) {
                    const data = await res.json();
                    const sel = document.getElementById('selHistoryRetention');
                    if (sel && data.retention_days !== undefined) {
                        sel.value = String(data.retention_days);
                    }
                    const lbl = document.getElementById('historyStatsLabel');
                    if (lbl) {
                        lbl.textContent = `Tổng: ${data.total_records || 0} bản ghi (${data.storage_mb || 0} MB)`;
                    }
                }
            } catch (e) {
                console.error("Error loading history settings:", e);
            }
        }

        async function saveHistorySettings() {
            const sel = document.getElementById('selHistoryRetention');
            const days = parseInt(sel.value, 10);
            try {
                const res = await fetch('/api/history/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ retention_days: days })
                });
                if (res.ok) {
                    const data = await res.json();
                    showToast(`✓ Đã lưu lịch tự động xóa: ${days === 0 ? "Không bao giờ" : days + " ngày"}`);
                    await loadHistorySettings();
                    await loadHistoryData();
                } else {
                    showToast("Lỗi khi lưu cài đặt lịch!", true);
                }
            } catch (e) {
                showToast("Lỗi kết nối máy chủ!", true);
            }
        }

        async function loadHistoryData() {
            const listEl = document.getElementById('historyListContent');
            listEl.innerHTML = `<div style="padding: 30px; text-align: center; color: #94a3b8; font-size: 13px;">Đang tải lịch sử...</div>`;
            try {
                let url = '/api/history?limit=100';
                if (currentHistoryFilter) url += `&type=${currentHistoryFilter}`;
                const res = await fetch(url);
                if (res.ok) {
                    const data = await res.json();
                    currentHistoryRecords = data.records || [];
                    if (data.settings) {
                        const lbl = document.getElementById('historyStatsLabel');
                        if (lbl) lbl.textContent = `Tổng: ${data.settings.total_records || 0} bản ghi (${data.settings.storage_mb || 0} MB)`;
                    }
                    renderHistoryList();
                } else {
                    listEl.innerHTML = `<div style="padding: 30px; text-align: center; color: #f87171; font-size: 13px;">Không thể tải danh sách lịch sử.</div>`;
                }
            } catch (e) {
                listEl.innerHTML = `<div style="padding: 30px; text-align: center; color: #f87171; font-size: 13px;">Lỗi kết nối khi tải lịch sử.</div>`;
            }
        }

        function renderHistoryList() {
            const listEl = document.getElementById('historyListContent');
            let filtered = currentHistoryRecords;
            if (currentHistoryFilter) {
                filtered = filtered.filter(r => r.type === currentHistoryFilter);
            }

            if (!filtered || filtered.length === 0) {
                listEl.innerHTML = `
                    <div style="padding: 40px; text-align: center; color: #64748b;">
                        <span style="font-size: 32px; display: block; margin-bottom: 8px;">📭</span>
                        Không có dữ liệu lịch sử nào phù hợp.
                    </div>
                `;
                return;
            }

            let html = `
                <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                    <thead>
                        <tr style="background: #182234; color: #94a3b8; border-bottom: 1px solid var(--border-color); font-size: 12px;">
                            <th style="padding: 10px 14px; width: 140px;">Thời Gian</th>
                            <th style="padding: 10px 14px; width: 160px;">Thiết Bị / Phòng</th>
                            <th style="padding: 10px 14px; width: 110px;">Loại</th>
                            <th style="padding: 10px 14px;">Nội Dung (Văn Bản & Phản Hồi)</th>
                            <th style="padding: 10px 14px; width: 230px;">Ghi Âm</th>
                            <th style="padding: 10px 14px; width: 50px; text-align: center;">Xóa</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            filtered.forEach(r => {
                const isAi = r.type === 'voice_ai';
                const typeBadge = isAi ? 
                    `<span style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;">🤖 AI Voice</span>` :
                    `<span style="background: rgba(16, 185, 129, 0.2); color: #34d399; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;">🎙️ Intercom</span>`;

                let audioPlayer = `<span style="color: #64748b; font-size: 12px;">Không có file</span>`;
                if (r.audio_file) {
                    audioPlayer = `
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <audio controls preload="none" style="height: 30px; width: 180px;">
                                <source src="/api/history/audio/${escapeHtml(r.audio_file)}" type="audio/wav">
                            </audio>
                            <span style="font-size: 11px; color: #94a3b8;">${r.duration || 0}s</span>
                        </div>
                    `;
                }

                let contentHtml = `<div><strong style="color: #f1f5f9;">Nói:</strong> <span style="color: #e2e8f0;">"${escapeHtml(r.text || '')}"</span></div>`;
                if (r.response) {
                    contentHtml += `<div style="margin-top: 4px;"><strong style="color: #10b981;">AI:</strong> <span style="color: #cbd5e1;">${escapeHtml(r.response)}</span></div>`;
                }

                html += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.15s;" onmouseover="this.style.background='rgba(255,255,255,0.02)'" onmouseout="this.style.background='transparent'">
                        <td style="padding: 10px 14px; color: #94a3b8; font-size: 12px;">${escapeHtml(r.datetime || '')}</td>
                        <td style="padding: 10px 14px;">
                            <div style="font-weight: 600; color: #f1f5f9;">${escapeHtml(r.room_name || 'Phòng')}</div>
                            <div style="font-size: 11px; color: #64748b;">Mã: [${escapeHtml(r.device_code || '')}]</div>
                        </td>
                        <td style="padding: 10px 14px;">${typeBadge}</td>
                        <td style="padding: 10px 14px;">${contentHtml}</td>
                        <td style="padding: 10px 14px;">${audioPlayer}</td>
                        <td style="padding: 10px 14px; text-align: center;">
                            <button onclick="deleteHistoryItem('${escapeHtml(r.id)}')" style="background: transparent; border: none; color: #94a3b8; cursor: pointer; font-size: 14px; padding: 4px;" title="Xóa bản ghi này" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='#94a3b8'">
                                🗑️
                            </button>
                        </td>
                    </tr>
                `;
            });

            html += `</tbody></table>`;
            listEl.innerHTML = html;
        }

        async function deleteHistoryItem(id) {
            try {
                const res = await fetch(`/api/history/${encodeURIComponent(id)}`, { method: 'DELETE' });
                if (res.ok) {
                    currentHistoryRecords = currentHistoryRecords.filter(r => r.id !== id);
                    renderHistoryList();
                    loadHistorySettings();
                    showToast("Đã xóa bản ghi");
                } else {
                    showToast("Lỗi khi xóa bản ghi", true);
                }
            } catch (e) {
                showToast("Lỗi kết nối!", true);
            }
        }

        async function confirmClearAllHistory() {
            if (!confirm("Bạn có chắc chắn muốn xóa TOÀN BỘ lịch sử và file âm thanh ghi âm không? Hành động này không thể hoàn tác!")) {
                return;
            }
            try {
                const res = await fetch('/api/history', { method: 'DELETE' });
                if (res.ok) {
                    currentHistoryRecords = [];
                    renderHistoryList();
                    loadHistorySettings();
                    showToast("✓ Đã xóa sạch toàn bộ lịch sử");
                } else {
                    showToast("Lỗi khi dọn sạch lịch sử", true);
                }
            } catch (e) {
                showToast("Lỗi kết nối!", true);
            }
        }

        function handleNewHistoryRecord(rec) {
            if (!rec) return;
            currentHistoryRecords.unshift(rec);
            if (isHistoryModalOpen) {
                renderHistoryList();
                loadHistorySettings();
            }
        }

        // -------------------------------------------------------------------------
        // 7. REST DATA BOOTSTRAP
        // -------------------------------------------------------------------------
        async function fetchInitialData() {
            try {
                const [devRes, entRes, sysRes, areaRes, floorsRes] = await Promise.all([
                    fetch('/api/devices'),
                    fetch('/api/ha/entities'),
                    fetch('/api/system/status'),
                    fetch('/api/ha/areas'),
                    fetch('/api/all-house/floors-overview')
                ]);

                if (areaRes && areaRes.ok) {
                    const areaData = await areaRes.json();
                    haAreasList = areaData.areas || [];
                    haFloorsList = areaData.floors || [];
                }
                if (devRes.ok) {
                    currentDevices = await devRes.json();
                    renderDevices();
                }
                if (entRes.ok) {
                    currentEntities = await entRes.json();
                    currentEntities.forEach(e => { entityStates[e.entity_id] = e.state; });
                    populateHAEntityDropdown();
                }
                if (sysRes.ok) {
                    const sys = await sysRes.json();
                    updateSystemStatus(sys);
                }
                if (floorsRes && floorsRes.ok) {
                    const fData = await floorsRes.json();
                    if (fData.overview) updateFloorsOverview(fData.overview);
                    if (fData.house_status) updateAllHouseStrip(fData.house_status);
                }
            } catch (e) {
                console.warn("Bootstrap REST fetch warning:", e);
            }
        }

        // Initialize on load
        window.addEventListener('DOMContentLoaded', () => {
            fetchInitialData();
            initWebSocket();
        });
    