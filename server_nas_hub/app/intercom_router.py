"""
NALA SMART HOME - ADVANCED INTERCOM ROUTER
Direct binary PCM 520-byte packet relay between satellite nodes, wall panels, and Web Admin.
Supports Dynamic ID Assignment, Peer-to-Peer Unicast, House Broadcast (0xFF), and Web PTT Intercom.
"""

import logging
import time
import asyncio
from typing import Dict, Set, Optional, List
from fastapi import WebSocket

logger = logging.getLogger("IntercomRouter")

class IntercomRouter:
    def __init__(self):
        # device_key (pairing_code or identifier) -> WebSocket connection
        self.connections: Dict[str, WebSocket] = {}
        # intercom_id (uint8 1..250) -> device_key
        self.id_to_device: Dict[int, str] = {}
        # device_key -> intercom_id
        self.device_to_id: Dict[str, int] = {}
        # Web Admin sockets listening to intercom audio
        self.admin_sockets: Set[WebSocket] = set()
        # Metadata cache: device_key -> {room_name, floor}
        self.device_meta: Dict[str, dict] = {}
        # Hands-free active calls: device_key -> session dict
        self.active_handsfree_sessions: Dict[str, dict] = {}

    def assign_id(self, device_key: str, preferred_id: Optional[int] = None) -> int:
        """Gán hoặc lấy intercom_id duy nhất cho thiết bị."""
        if device_key in self.device_to_id:
            return self.device_to_id[device_key]

        if preferred_id and preferred_id not in self.id_to_device and 1 <= preferred_id <= 250:
            assigned = preferred_id
        else:
            assigned = 1
            while assigned in self.id_to_device and assigned < 250:
                assigned += 1

        self.id_to_device[assigned] = device_key
        self.device_to_id[device_key] = assigned
        logger.info("Assigned Intercom ID %d to device [%s]", assigned, device_key)
        return assigned

    def register(self, device_key: str, websocket: WebSocket, intercom_id: Optional[int] = None, meta: Optional[dict] = None) -> int:
        """Đăng ký kết nối WebSocket và liên kết intercom_id."""
        self.connections[device_key] = websocket
        if meta:
            self.device_meta[device_key] = meta
        assigned_id = self.assign_id(device_key, intercom_id)
        logger.info("Registered Intercom device [%s] (ID: %d)", device_key, assigned_id)
        return assigned_id

    def register_admin(self, websocket: WebSocket):
        """Đăng ký Web Admin để nhận stream âm thanh đàm thoại."""
        self.admin_sockets.add(websocket)
        logger.info("Registered Web Admin for Intercom audio (Total: %d)", len(self.admin_sockets))

    def unregister_admin(self, websocket: WebSocket):
        self.admin_sockets.discard(websocket)

    def unregister(self, device_key: str, websocket: Optional[WebSocket] = None):
        if device_key in self.connections:
            if websocket is not None and self.connections[device_key] != websocket:
                return  # Socket moi da thay the socket cu, khong huy dang ky!
            del self.connections[device_key]
            logger.info("Unregistered Intercom device [%s]", device_key)

    def get_id(self, device_key: str) -> Optional[int]:
        return self.device_to_id.get(device_key)

    def get_device(self, intercom_id: int) -> Optional[str]:
        return self.id_to_device.get(intercom_id)

    def get_targets(self, exclude_device_key: Optional[str] = None) -> List[dict]:
        """Trả về danh sách các kênh Intercom có thể gọi đến trong hệ thống."""
        targets = []
        for i_id, d_key in sorted(self.id_to_device.items()):
            if exclude_device_key and d_key == exclude_device_key:
                continue
            meta = self.device_meta.get(d_key, {})
            is_online = d_key in self.connections
            targets.append({
                "id": i_id,
                "code": d_key,
                "name": meta.get("room_name", f"Panel {d_key}"),
                "floor": meta.get("floor", ""),
                "online": is_online
            })
        return targets

    def start_handsfree_call(self, caller_key: str, target_key: str) -> Optional[dict]:
        """Bắt đầu phiên đàm thoại rảnh tay 2 chiều giữa 2 màn hình."""
        caller_id = self.device_to_id.get(caller_key, 1)
        target_id = self.device_to_id.get(target_key, 2)
        caller_meta = self.device_meta.get(caller_key, {})
        target_meta = self.device_meta.get(target_key, {})

        # Kết thúc bất kỳ phiên cũ nào trước đó của 2 bên
        self.end_handsfree_call(caller_key, reason="new_call")
        self.end_handsfree_call(target_key, reason="new_call")

        now = time.time()
        sess_id = f"call_{caller_key}_{target_key}_{int(now)}"
        session = {
            "session_id": sess_id,
            "caller_key": caller_key,
            "caller_id": caller_id,
            "caller_room": caller_meta.get("room_name", f"Panel {caller_key}"),
            "target_key": target_key,
            "target_id": target_id,
            "target_room": target_meta.get("room_name", f"Panel {target_key}"),
            "start_time": now,
            "last_audio_time": now,
            "active_speaker": None,
            "speaker_release_time": 0.0,
            "warning_sent": False,
            "state": "active"
        }
        self.active_handsfree_sessions[caller_key] = session
        self.active_handsfree_sessions[target_key] = session
        logger.info("📞 Started Handsfree Intercom call: [%s] (%s) <--> [%s] (%s)",
                    caller_key, session["caller_room"], target_key, session["target_room"])
        return session

    def get_active_session_for_device(self, device_key: str) -> Optional[dict]:
        """Lấy phiên gọi rảnh tay đang diễn ra của thiết bị (nếu có)."""
        return self.active_handsfree_sessions.get(device_key)

    def end_handsfree_call(self, device_key: str, reason: str = "hangup") -> Optional[dict]:
        """Kết thúc phiên đàm thoại rảnh tay của thiết bị và phòng đối diện."""
        session = self.active_handsfree_sessions.get(device_key)
        if not session:
            return None

        caller_k = session.get("caller_key")
        target_k = session.get("target_key")

        self.active_handsfree_sessions.pop(caller_k, None)
        self.active_handsfree_sessions.pop(target_k, None)

        session["state"] = "ended"
        session["end_reason"] = reason
        session["duration"] = round(time.time() - session.get("start_time", time.time()), 1)
        logger.info("🛑 Ended Handsfree Intercom call %s (Reason: %s, Duration: %ss)",
                    session.get("session_id"), reason, session.get("duration"))
        return session

    def get_active_calls_summary(self) -> List[dict]:
        """Danh sách các cuộc gọi đang diễn ra để hiển thị trên Web Admin."""
        seen_sessions = set()
        res = []
        now = time.time()
        for dev_k, sess in list(self.active_handsfree_sessions.items()):
            sid = sess.get("session_id")
            if sid and sid not in seen_sessions:
                seen_sessions.add(sid)
                res.append({
                    "session_id": sid,
                    "caller_key": sess.get("caller_key"),
                    "caller_room": sess.get("caller_room"),
                    "target_key": sess.get("target_key"),
                    "target_room": sess.get("target_room"),
                    "duration": int(now - sess.get("start_time", now)),
                    "last_active": int(now - sess.get("last_audio_time", now))
                })
        return res

    async def check_silence_watchdogs(self, on_warning_cb=None, on_hangup_cb=None):
        """Kiểm tra thời gian im lặng (Watchdog 10s):
        - Nếu im lặng >= 10s: Cảnh báo bíp bíp và đếm ngược 3s
        - Nếu im lặng >= 13s: Tự động cúp máy an toàn
        """
        now = time.time()
        processed_sids = set()

        for dev_k, sess in list(self.active_handsfree_sessions.items()):
            sid = sess.get("session_id")
            if not sid or sid in processed_sids or sess.get("state") != "active":
                continue
            processed_sids.add(sid)

            silence_sec = now - sess.get("last_audio_time", now)

            # 1. Cảnh báo im lặng 10s
            if silence_sec >= 10.0 and not sess.get("warning_sent", False):
                sess["warning_sent"] = True
                logger.info("⚠️ Silence watchdog 10s triggered for call %s", sid)
                if on_warning_cb:
                    try:
                        res = on_warning_cb(sess)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as ex:
                        logger.warning("Error in on_warning_cb: %s", ex)

            # 2. Cúp máy sau 13s im lặng liên tục
            if silence_sec >= 13.0:
                logger.info("⏱️ Silence watchdog 13s expired: auto-hanging up call %s", sid)
                ended_sess = self.end_handsfree_call(sess.get("caller_key"), reason="silence_timeout")
                if on_hangup_cb and ended_sess:
                    try:
                        res = on_hangup_cb(ended_sess, "silence_timeout")
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as ex:
                        logger.warning("Error in on_hangup_cb: %s", ex)

    async def route_binary_packet(self, sender_key: str, packet: bytes):
        """
        Định tuyến gói tin Audio (Raw PCM 520B hoặc Nén Opus 0xA55B):
        - 0x00: AI Voice processing (bỏ qua ở router này)
        - 0xFF: Broadcast toàn bộ các màn hình
        - 0xFE: Riêng cho Web Admin Hub
        - 1..250: Unicast tới màn hình có intercom_id tương ứng
        """
        is_pcm = (len(packet) == 520 and packet[0] == 0x5A and packet[1] == 0xA5)
        is_opus = (len(packet) >= 9 and packet[0] == 0x5B and packet[1] == 0xA5)
        if not (is_pcm or is_opus):
            return

        # KIỂM SOÁT VOICE-SWITCHING (TRIỆT TIÊU VỌNG ÂM & HÚ RÍT)
        sess = self.get_active_session_for_device(sender_key)
        if sess and sess.get("state") == "active":
            now = time.time()
            other_key = sess["target_key"] if sender_key == sess["caller_key"] else sess["caller_key"]
            # Nếu bên đối diện vừa phát âm thanh và chưa hết thời gian nhả loa (150ms release)
            if sess.get("active_speaker") == other_key and now < sess.get("speaker_release_time", 0):
                # Khóa mic bên nhận trong khi loa bên nhận đang phát -> triệt tiêu 100% vòng lặp âm thanh
                return

            sess["active_speaker"] = sender_key
            sess["speaker_release_time"] = now + 0.150  # 150ms nhả mic
            sess["last_audio_time"] = now
            sess["warning_sent"] = False

        sender_id = packet[2]
        target_id = packet[3]
        stream_flag = packet[6]

        if target_id == 0x00:
            return

        # 1. BROADCAST TOÀN NHÀ (0xFF)
        if target_id == 0xFF:
            for dev_key, ws in list(self.connections.items()):
                if dev_key != sender_key:
                    try:
                        await ws.send_bytes(packet)
                    except Exception as e:
                        logger.error("Error broadcasting intercom to [%s]: %s", dev_key, e)

            # Chuyển tiếp tới Web Admin (nếu người gửi không phải admin)
            if not sender_key.startswith("web_admin"):
                for admin_ws in list(self.admin_sockets):
                    try:
                        await admin_ws.send_bytes(packet)
                    except Exception:
                        pass
            return

        # 2. GỬI RIÊNG CHO WEB ADMIN (0xFE)
        if target_id == 0xFE:
            for admin_ws in list(self.admin_sockets):
                try:
                    await admin_ws.send_bytes(packet)
                except Exception:
                    pass
            return

        # 3. UNICAST TỚI MÀN HÌNH CỤ THỂ
        target_key = self.id_to_device.get(target_id)
        if target_key and target_key in self.connections:
            try:
                await self.connections[target_key].send_bytes(packet)
            except Exception as e:
                logger.error("Error sending unicast intercom to [%s]: %s", target_key, e)

        # Chuyển tiếp bản sao tới Web Admin để admin có thể nghe được các cuộc gọi Unicast (giám sát)
        if not sender_key.startswith("web_admin"):
            for admin_ws in list(self.admin_sockets):
                try:
                    await admin_ws.send_bytes(packet)
                except Exception:
                    pass
