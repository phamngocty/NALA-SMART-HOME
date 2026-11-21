"""
==============================================================================
NALA SMART HOME - NATURAL LANGUAGE CONTEXTUAL AUTOMATION ENGINE
- Quản lý và thực thi các kịch bản tự động hóa phi tuyến tính dựa trên Ngữ cảnh Sống
- Hỗ trợ các Trigger:
  + living_context (deep_sleep, night_wakeup, active, empty, approaching)
  + speaker (nhận diện theo vân giọng: Anh Ty, Me, ...)
  + time_range (ví dụ: 22:30 - 06:30)
  + lux_range (ví dụ: <= 15 lx)
- Tự động lưu trữ vào data/automations.json
- Tích hợp AI Parser để biên dịch câu nói tự nhiên thành JSON Rule
==============================================================================
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

logger = logging.getLogger("NalaAutomation")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [AUTOMATION] %(message)s")


class AutomationEngine:
    def __init__(self, ha_bridge=None, storage_path: Optional[str] = None):
        self.ha_bridge = ha_bridge
        self.rules: List[Dict[str, Any]] = []
        
        # Đường dẫn lưu trữ rules
        candidates = [
            storage_path,
            "/app/data/automations.json",
            "data/automations.json",
            os.path.join(os.path.dirname(__file__), "data", "automations.json"),
            "/home/nas152/nala-voice-intercom-system/server_nas_hub/data/automations.json"
        ]
        chosen = None
        for p in candidates:
            if p:
                try:
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    chosen = p
                    break
                except Exception:
                    continue
        self.storage_path = chosen or "/tmp/nala_automations.json"
        self._load_rules()

    def _load_rules(self):
        """Nạp danh sách kịch bản từ file JSON."""
        if os.path.isfile(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self.rules = json.load(f)
                logger.info("Đã nạp %d kịch bản tự động hóa từ %s", len(self.rules), self.storage_path)
            except Exception as e:
                logger.error("Lỗi đọc file kịch bản: %s", e)
                self.rules = []
        else:
            # Tạo các kịch bản mặc định thông minh nếu chưa có
            self._create_default_rules()
            self._save_rules()

    def _save_rules(self):
        """Lưu danh sách kịch bản vào file JSON."""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Lỗi lưu file kịch bản: %s", e)

    def _create_default_rules(self):
        """Các kịch bản tự động hóa chuẩn mực chống bật đèn chói mắt và dẫn đường đêm."""
        self.rules = [
            {
                "id": "rule_night_sleep_guard",
                "name": "Bảo vệ giấc ngủ sâu (Deep Sleep Guard)",
                "description": "Khi phòng ngủ ở trạng thái ngủ say, duy trì máy lạnh 26 độ êm dịu và triệt tiêu đèn trần",
                "enabled": True,
                "trigger": {
                    "type": "living_context",
                    "state": "deep_sleep"
                },
                "conditions": {
                    "time_range": {"start": "22:30", "end": "06:30"},
                    "max_lux": 15
                },
                "actions": [
                    {
                        "domain": "climate",
                        "service": "set_temperature",
                        "data": {"temperature": 26.0}
                    }
                ]
            },
            {
                "id": "rule_night_path_light",
                "name": "Đèn dẫn đường thức giấc đêm (Night Path Light)",
                "description": "Khi thức giấc ban đêm, chỉ bật đèn ngủ hoặc đèn hắt dịu mắt 10%, không làm chói mắt",
                "enabled": True,
                "trigger": {
                    "type": "living_context",
                    "state": "night_wakeup"
                },
                "conditions": {
                    "time_range": {"start": "00:00", "end": "05:45"},
                    "max_lux": 15
                },
                "actions": [
                    {
                        "domain": "light",
                        "service": "turn_on",
                        "data": {"brightness_pct": 10}
                    }
                ]
            },
            {
                "id": "rule_empty_room_powersave",
                "name": "Tiết kiệm điện khi rời phòng (Empty Room Eco)",
                "description": "Khi phòng vắng người liên tục, tự động tắt bớt đèn chiếu sáng",
                "enabled": True,
                "trigger": {
                    "type": "living_context",
                    "state": "empty"
                },
                "conditions": {
                    "min_duration_sec": 300
                },
                "actions": [
                    {
                        "domain": "light",
                        "service": "turn_off"
                    }
                ]
            }
        ]

    def list_rules(self) -> List[Dict[str, Any]]:
        return self.rules

    def add_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in rule:
            rule["id"] = f"rule_{int(time.time())}"
        if "enabled" not in rule:
            rule["enabled"] = True
        self.rules.append(rule)
        self._save_rules()
        logger.info("Đã thêm kịch bản mới: %s (%s)", rule.get("name"), rule.get("id"))
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        before = len(self.rules)
        self.rules = [r for r in self.rules if r.get("id") != rule_id]
        if len(self.rules) < before:
            self._save_rules()
            logger.info("Đã xóa kịch bản: %s", rule_id)
            return True
        return False

    def toggle_rule(self, rule_id: str, enabled: bool) -> bool:
        for r in self.rules:
            if r.get("id") == rule_id:
                r["enabled"] = enabled
                self._save_rules()
                return True
        return False

    def update_rule(self, rule_id: str, updated_rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Cập nhật kịch bản đã có."""
        for i, r in enumerate(self.rules):
            if r.get("id") == rule_id:
                updated_rule["id"] = rule_id
                if "enabled" not in updated_rule:
                    updated_rule["enabled"] = r.get("enabled", True)
                self.rules[i] = updated_rule
                self._save_rules()
                logger.info("Đã cập nhật kịch bản: %s (%s)", updated_rule.get("name"), rule_id)
                return updated_rule
        return None

    def parse_and_register_automation(self, text: str, context_room: str = "", speaker_name: Optional[str] = None) -> Optional[str]:
        """
        Phân tích câu lệnh giọng nói tự nhiên và tự động đăng ký kịch bản mới.
        Ví dụ: "Khi anh ngủ thì chỉnh máy lạnh 27 độ"
        Trả về câu thông báo xác nhận nếu đăng ký thành công, hoặc None nếu không phải lệnh tạo rule.
        """
        import re
        norm = text.lower().strip()

        # Kiểm tra từ khóa kích hoạt kịch bản
        is_auto_intent = any(k in norm for k in [
            "cài đặt tự động", "cài tự động", "tự động hóa", "mỗi khi", "khi nào",
            "tạo kịch bản", "lập kịch bản", "nếu tôi ngủ", "khi tôi ngủ", "khi anh ngủ",
            "khi thức giấc", "khi vắng người", "khi rời phòng", "khi em ngủ"
        ])
        if not is_auto_intent:
            return None

        # 1. Nhận diện Trigger
        trigger_state = None
        trigger_name = ""
        if any(w in norm for w in ["ngủ", "ngủ say", "đi ngủ", "ngu"]):
            trigger_state = "deep_sleep"
            trigger_name = "ngủ say"
        elif any(w in norm for w in ["thức giấc", "dậy ban đêm", "đi vệ sinh", "thuc giac"]):
            trigger_state = "night_wakeup"
            trigger_name = "thức giấc ban đêm"
        elif any(w in norm for w in ["vắng người", "không có ai", "rời phòng", "khong co ai"]):
            trigger_state = "empty"
            trigger_name = "phòng vắng người"
        elif any(w in norm for w in ["vào phòng", "lại gần", "tới gần", "den gan"]):
            trigger_state = "approaching"
            trigger_name = "tiến lại gần"

        if not trigger_state:
            return None

        # 2. Nhận diện Actions
        actions = []
        action_desc = []

        # Máy lạnh / điều hòa
        if any(w in norm for w in ["máy lạnh", "điều hòa", "ac", "may lanh", "dieu hoa"]):
            temp_match = re.search(r"(\d{2})\s*(?:độ|°c|c)?", norm)
            target_temp = float(temp_match.group(1)) if temp_match else 26.0
            actions.append({
                "domain": "climate",
                "service": "set_temperature",
                "data": {"temperature": target_temp}
            })
            action_desc.append(f"chỉnh điều hòa {int(target_temp)} độ")

        # Đèn
        if any(w in norm for w in ["đèn", "den"]):
            if any(w in norm for w in ["tắt", "đóng", "tat"]):
                actions.append({"domain": "light", "service": "turn_off"})
                action_desc.append("tắt đèn")
            elif any(w in norm for w in ["bật", "mở", "bat"]):
                bright = 10 if any(w in norm for w in ["ngủ", "mờ", "dịu", "vang"]) else 100
                actions.append({
                    "domain": "light",
                    "service": "turn_on",
                    "data": {"brightness_pct": bright}
                })
                action_desc.append(f"bật đèn {bright}%")

        if not actions:
            return None

        # 3. Tạo Rule
        rule_name = f"Tự động khi {trigger_name} ({context_room or 'Phòng'})"
        rule = {
            "id": f"rule_usr_{int(time.time())}",
            "name": rule_name,
            "description": f"Kịch bản do {speaker_name or 'người dùng'} thiết lập qua giọng nói",
            "enabled": True,
            "trigger": {
                "type": "living_context",
                "state": trigger_state
            },
            "conditions": {
                "occupant": speaker_name if speaker_name else None
            },
            "actions": actions
        }
        self.add_rule(rule)
        actions_str = " và ".join(action_desc)
        return f"Dạ, Nala đã ghi nhớ kịch bản thông minh: mỗi khi {trigger_name}, em sẽ tự động {actions_str} cho bạn ạ!"

    def _check_time_condition(self, t_cond: Dict[str, str]) -> bool:
        """Kiểm tra điều kiện giờ."""
        if not t_cond:
            return True
        now = datetime.now()
        cur_min = now.hour * 60 + now.minute
        try:
            s_parts = [int(p) for p in t_cond.get("start", "00:00").split(":")]
            e_parts = [int(p) for p in t_cond.get("end", "23:59").split(":")]
            start_min = s_parts[0] * 60 + s_parts[1]
            end_min = e_parts[0] * 60 + e_parts[1]
            if start_min > end_min:
                return cur_min >= start_min or cur_min < end_min
            else:
                return start_min <= cur_min < end_min
        except Exception:
            return True

    async def evaluate_living_context_trigger(self, room_id: str, room_name: str, new_state: str, context_dict: Dict[str, Any]):
        """
        Được gọi mỗi khi một phòng thay đổi trạng thái Living Context FSM.
        Duyệt qua các rule và thực thi action tương ứng.
        """
        telemetry = context_dict.get("telemetry", {})
        lux = telemetry.get("light_lux", 0)
        occupant = context_dict.get("occupant")

        for rule in self.rules:
            if not rule.get("enabled", True):
                continue

            trigger = rule.get("trigger", {})
            if trigger.get("type") == "living_context":
                target_state = trigger.get("state")
                if target_state != new_state:
                    continue

                # Kiểm tra Conditions
                conds = rule.get("conditions", {})
                
                # Điều kiện thời gian
                if "time_range" in conds and not self._check_time_condition(conds["time_range"]):
                    continue

                # Điều kiện độ sáng
                if "max_lux" in conds and lux > conds["max_lux"]:
                    continue
                if "min_lux" in conds and lux < conds["min_lux"]:
                    continue

                # Điều kiện người dùng (speaker)
                if "occupant" in conds and conds["occupant"]:
                    if occupant != conds["occupant"]:
                        continue

                # Điều kiện phòng áp dụng (target_room)
                if "target_room" in conds and conds["target_room"]:
                    t_room = str(conds["target_room"]).lower().strip()
                    if t_room and t_room != "all" and t_room != "toàn nhà":
                        r_name = (room_name or "").lower()
                        r_id = (room_id or "").lower()
                        if t_room not in r_name and t_room not in r_id:
                            continue

                # THỎA MÃN MỌI ĐIỀU KIỆN -> THỰC THI ACTIONS
                logger.info("[AUTOMATION] ⚡ Kích hoạt kịch bản '%s' tại [%s] (Trạng thái: %s)",
                            rule.get("name"), room_name or room_id, new_state)
                await self._execute_actions(rule.get("actions", []), room_name or room_id)

    async def _execute_actions(self, actions: List[Dict[str, Any]], room_name: str):
        """Thực thi danh sách hành động qua ha_bridge."""
        if not self.ha_bridge:
            return

        for act in actions:
            domain = act.get("domain", "light")
            service = act.get("service", "turn_on")
            entity_id = act.get("entity_id")
            data = act.get("data", {})

            # Nếu không chỉ định entity_id cụ thể, tìm thiết bị tương ứng trong phòng
            if not entity_id and hasattr(self.ha_bridge, "get_entities_list"):
                all_ents = self.ha_bridge.get_entities_list()
                for e in all_ents:
                    e_dom = e.get("domain", "")
                    e_area = (e.get("area_name") or "").lower()
                    r_norm = room_name.lower()
                    if e_dom == domain and (r_norm in e_area or e_area in r_norm):
                        entity_id = e.get("entity_id")
                        break

            if entity_id:
                try:
                    await self.ha_bridge.call_service(domain, service, entity_id=entity_id, service_data=data)
                    logger.info("[AUTOMATION] Đã thực thi %s.%s trên %s", domain, service, entity_id)
                except Exception as e:
                    logger.warning("[AUTOMATION] Lỗi thực thi action %s.%s: %s", domain, service, e)


# Singleton instance toàn cục
automationEngine = AutomationEngine()
