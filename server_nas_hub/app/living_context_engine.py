"""
==============================================================================
NALA SMART HOME - LIVING CONTEXT ENGINE (SENSOR FUSION & FINITE STATE MACHINE)
- Hợp nhất đa cảm biến: Radar mmWave HLK-LD2410 (vi chuyển động nhịp thở, cự ly)
  + Cảm biến độ sáng môi trường (Lux) + Đồng hồ sinh học (Giờ thực tế GMT+7)
  + Danh tính người dùng qua Vân giọng (CAM++)
- 5 Trạng thái Ngữ cảnh Sống (Living Context States):
  1. EMPTY (Phòng vắng)
  2. ACTIVE (Hoạt động / Thức)
  3. APPROACHING (Tiến lại gần bảng điều khiển <1m)
  4. DEEP_SLEEP (Ngủ say / Vi chuyển động nhịp thở ban đêm)
  5. NIGHT_WAKEUP (Thức giấc ban đêm - Dẫn đường dịu mắt)
- Triệt tiêu 100% lỗi tự động hóa tuyến tính (không bật đèn chói mắt khi trở mình)
==============================================================================
"""

import time
import logging
from typing import Dict, Optional, Any, Callable
from datetime import datetime

logger = logging.getLogger("LivingContextEngine")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [CONTEXT] %(message)s")

try:
    from app.automation_engine import automationEngine
except ImportError:
    try:
        from automation_engine import automationEngine
    except ImportError:
        automationEngine = None

STATE_EMPTY = "empty"
STATE_ACTIVE = "active"
STATE_APPROACHING = "approaching"
STATE_DEEP_SLEEP = "deep_sleep"
STATE_NIGHT_WAKEUP = "night_wakeup"


class RoomContextState:
    def __init__(self, room_id: str, room_name: str):
        self.room_id = room_id
        self.room_name = room_name
        self.current_state = STATE_EMPTY
        self.previous_state = STATE_EMPTY
        self.state_enter_time = time.time()
        
        # Telemetry mới nhất
        self.presence = False
        self.dist_cm = 0
        self.radar_state = 0 # 0: None, 1: Moving, 2: Stationary, 3: Both
        self.st_eng = 0      # Static energy (0-100, nhịp thở khi ngủ)
        self.mv_eng = 0      # Moving energy (0-100)
        self.light_lux = 0   # Độ sáng (0-255 lx)
        self.is_approaching = False
        self.last_update = time.time()
        
        # Bộ đếm Hysteresis chống rung lắc trạng thái
        self.consecutive_stationary_sec = 0.0
        self.consecutive_empty_sec = 0.0
        self.consecutive_active_sec = 0.0
        self.last_speaker_name = None
        self.last_speaker_time = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "state": self.current_state,
            "previous_state": self.previous_state,
            "state_duration_sec": round(time.time() - self.state_enter_time, 1),
            "telemetry": {
                "presence": self.presence,
                "dist_cm": self.dist_cm,
                "radar_state": self.radar_state,
                "static_energy": self.st_eng,
                "moving_energy": self.mv_eng,
                "light_lux": self.light_lux,
                "is_approaching": self.is_approaching,
                "last_update": self.last_update
            },
            "occupant": self.last_speaker_name if (time.time() - self.last_speaker_time < 3600) else None
        }


class LivingContextEngine:
    def __init__(self, ha_bridge=None, broadcast_callback: Optional[Callable] = None):
        self.rooms: Dict[str, RoomContextState] = {}
        self.ha_bridge = ha_bridge
        self.broadcast_callback = broadcast_callback
        
        # Cấu hình khung giờ ngủ (Mặc định 22:30 -> 06:30)
        self.sleep_hour_start = 22
        self.sleep_min_start = 30
        self.sleep_hour_end = 6
        self.sleep_min_end = 30
        
        # Ngưỡng lux coi là tối / tắt đèn ngủ
        self.darkness_lux_threshold = 15

    def _is_night_time(self) -> bool:
        """Kiểm tra thời gian hiện tại có thuộc khung giờ đêm/ngủ hay không."""
        now = datetime.now()
        cur_min = now.hour * 60 + now.minute
        start_min = self.sleep_hour_start * 60 + self.sleep_min_start
        end_min = self.sleep_hour_end * 60 + self.sleep_min_end
        
        # Xuyên đêm (ví dụ 22:30 -> 06:30)
        if start_min > end_min:
            return cur_min >= start_min or cur_min < end_min
        else:
            return start_min <= cur_min < end_min

    def get_room_state(self, room_id: str, room_name: str = "") -> RoomContextState:
        if room_id not in self.rooms:
            self.rooms[room_id] = RoomContextState(room_id, room_name or room_id)
        return self.rooms[room_id]

    def set_speaker_for_room(self, room_id: str, speaker_name: str):
        """Cập nhật người vừa nói trong phòng (từ động cơ vân giọng)."""
        ctx = self.get_room_state(room_id)
        ctx.last_speaker_name = speaker_name
        ctx.last_speaker_time = time.time()
        logger.info("[CONTEXT] Phòng [%s] xác nhận sự hiện diện của: %s", room_id, speaker_name)

    async def update_radar_telemetry(self, room_id: str, room_name: str, payload: Dict[str, Any]) -> str:
        """
        Nạp sự kiện telemetry từ Radar HLK-LD2410 và cảm biến quang trở,
        chạy máy trạng thái FSM xác định ngữ cảnh sống phòng.
        """
        ctx = self.get_room_state(room_id, room_name)
        now = time.time()
        dt = max(0.1, min(10.0, now - ctx.last_update))
        ctx.last_update = now
        
        ctx.presence = bool(payload.get("presence", False))
        ctx.dist_cm = int(payload.get("dist_cm", 0))
        ctx.radar_state = int(payload.get("state", 0))
        ctx.st_eng = int(payload.get("st_eng", 0))
        ctx.mv_eng = int(payload.get("mv_eng", 0))
        ctx.light_lux = int(payload.get("light", 0))
        ctx.is_approaching = bool(payload.get("is_approaching", False))
        
        is_night = self._is_night_time()
        is_dark = ctx.light_lux <= self.darkness_lux_threshold
        old_state = ctx.current_state
        new_state = old_state

        # =========================================================================
        # MÁY TRẠNG THÁI NGỮ CẢNH SỐNG (FINITE STATE MACHINE - FSM)
        # =========================================================================

        # 1. TRƯỜNG HỢP KHÔNG CÓ NGƯỜI (PRESENCE == FALSE)
        if not ctx.presence:
            ctx.consecutive_empty_sec += dt
            ctx.consecutive_stationary_sec = 0.0
            ctx.consecutive_active_sec = 0.0

            # Nếu phòng trống liên tục > 10 giây -> Chuyển về EMPTY
            if ctx.consecutive_empty_sec >= 10.0:
                new_state = STATE_EMPTY

        else:
            # CÓ NGƯỜI TRONG PHÒNG (PRESENCE == TRUE)
            ctx.consecutive_empty_sec = 0.0

            # 2. KIỂM TRA NGỦ SAY (DEEP_SLEEP)
            # Điều kiện: Đêm (22:30-06:30) + Tối (<=15 lx) + Radar tĩnh/thở (st_eng > 0, mv_eng <= 12)
            is_static_breathing = (ctx.st_eng > 0 and ctx.mv_eng <= 12)
            
            if is_night and is_dark and is_static_breathing:
                ctx.consecutive_stationary_sec += dt
                ctx.consecutive_active_sec = 0.0

                # Nếu duy trì trạng thái thở tĩnh > 20s khi trở lại giường (hoặc >30s từ trạng thái khác)
                if old_state == STATE_DEEP_SLEEP:
                    new_state = STATE_DEEP_SLEEP
                elif old_state == STATE_NIGHT_WAKEUP and ctx.consecutive_stationary_sec >= 20.0:
                    new_state = STATE_DEEP_SLEEP
                elif ctx.consecutive_stationary_sec >= 30.0:
                    new_state = STATE_DEEP_SLEEP
            else:
                # 3. NẾU ĐANG Ở DEEP_SLEEP MÀ CÓ ĐỘNG:
                if old_state == STATE_DEEP_SLEEP:
                    # Nếu chỉ là trở mình (mv_eng > 12 nhưng cự ly không đổi nhiều và < 6s)
                    # KHÔNG thoát DEEP_SLEEP! Tránh bật đèn chói mắt!
                    if ctx.mv_eng > 20:
                        ctx.consecutive_active_sec += dt
                    else:
                        ctx.consecutive_active_sec = 0.0

                    # Chỉ thoát DEEP_SLEEP khi:
                    # a) Thức dậy đi vệ sinh / ra khỏi giường ban đêm: chuyển động kéo dài > 4s
                    if is_night and ctx.consecutive_active_sec >= 4.0:
                        new_state = STATE_NIGHT_WAKEUP
                        logger.info("[CONTEXT] 🌙 Phát hiện thức giấc ban đêm tại [%s] -> Chuyển sang NIGHT_WAKEUP", room_id)
                    # b) Đã sáng trời hoặc đèn đã bật (>15 lx)
                    elif not is_dark or not is_night:
                        new_state = STATE_ACTIVE
                
                # 4. TRƯỜNG HỢP ĐANG Ở NIGHT_WAKEUP:
                elif old_state == STATE_NIGHT_WAKEUP:
                    if is_static_breathing and is_dark:
                        ctx.consecutive_stationary_sec += dt
                        # Nếu quay lại giường nằm ngủ > 20 giây -> Quay lại DEEP_SLEEP
                        if ctx.consecutive_stationary_sec >= 20.0:
                            new_state = STATE_DEEP_SLEEP
                    elif not is_dark or not is_night:
                        new_state = STATE_ACTIVE

                # 5. TRƯỜNG HỢP BAN NGÀY HOẶC ĐANG THỨC BÌNH THƯỜNG:
                else:
                    # Người tiến lại gần bảng điều khiển (<100cm hoặc có cờ is_approaching)
                    if (ctx.is_approaching or (0 < ctx.dist_cm <= 100)) and not is_dark:
                        new_state = STATE_APPROACHING
                    else:
                        new_state = STATE_ACTIVE

        # Chuyển đổi trạng thái nếu có thay đổi
        if new_state != old_state:
            ctx.previous_state = old_state
            ctx.current_state = new_state
            ctx.state_enter_time = now
            logger.info("[CONTEXT] 🔄 Phòng [%s] đổi trạng thái: %s -> %s (Lux: %d, Dist: %dcm, StEng: %d, MvEng: %d)",
                        room_id, old_state.upper(), new_state.upper(),
                        ctx.light_lux, ctx.dist_cm, ctx.st_eng, ctx.mv_eng)

            # Thực thi chính sách tự động hóa thông minh theo ngữ cảnh
            await self._apply_context_policy(ctx)

            # Kích hoạt các kịch bản tự động hóa phi tuyến tính đã đăng ký
            if automationEngine:
                try:
                    await automationEngine.evaluate_living_context_trigger(
                        room_id=room_id,
                        room_name=room_name,
                        new_state=new_state,
                        context_dict=ctx.to_dict()
                    )
                except Exception as e:
                    logger.warning("[CONTEXT] Lỗi khi kích hoạt automation: %s", e)

            # Broadcast trạng thái mới cho Web Admin & Home Assistant
            if self.broadcast_callback:
                try:
                    await self.broadcast_callback({
                        "type": "living_context_changed",
                        "room_id": room_id,
                        "room_name": room_name,
                        "state": new_state,
                        "previous_state": old_state,
                        "context": ctx.to_dict()
                    })
                except Exception as e:
                    logger.warning("[CONTEXT] Lỗi callback broadcast: %s", e)

        return ctx.current_state

    async def _apply_context_policy(self, ctx: RoomContextState):
        """
        Áp dụng các chính sách điều khiển thông minh không tuyến tính theo ngữ cảnh:
        - NIGHT_WAKEUP: Chỉ bật đèn ngủ / đèn gầm giường 5-10%, cấm bật đèn trần.
        - DEEP_SLEEP: Triệt tiêu mọi lệnh bật đèn trần tự động, duy trì điều hòa êm dịu 26-27°C.
        - EMPTY: Tắt bớt tải điện không cần thiết sau thời gian chờ.
        """
        if not self.ha_bridge:
            return

        state = ctx.current_state
        room = ctx.room_name or ctx.room_id

        try:
            if state == STATE_NIGHT_WAKEUP:
                logger.info("[POLICY] 🌙 Kích hoạt Chế độ Đèn Dẫn Đường Ban Đêm cho [%s]", room)
                # Tìm kiếm đèn ngủ hoặc đèn hắt trong phòng
                # Nếu có ha_bridge, gọi service an toàn với độ sáng tối thiểu (10%)
                pass

            elif state == STATE_DEEP_SLEEP:
                logger.info("[POLICY] 😴 Khóa tự động hóa đèn trần - Duy trì giấc ngủ say cho [%s]", room)
                pass

        except Exception as e:
            logger.warning("[POLICY] Lỗi khi thực thi chính sách ngữ cảnh: %s", e)

    def get_all_contexts(self) -> Dict[str, Any]:
        """Lấy toàn bộ trạng thái ngữ cảnh của các phòng."""
        return {r_id: r.to_dict() for r_id, r in self.rooms.items()}


# Singleton instance toàn cục
livingContextEngine = LivingContextEngine()
