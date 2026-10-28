"""
NALA SMART HOME - ADVANCED INTERCOM ROUTER
Direct binary PCM 520-byte packet relay between satellite nodes, wall panels, and Web Admin.
Supports Dynamic ID Assignment, Peer-to-Peer Unicast, House Broadcast (0xFF), and Web PTT Intercom.
"""

import logging
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

    def unregister(self, device_key: str):
        if device_key in self.connections:
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

    async def route_binary_packet(self, sender_key: str, packet: bytes):
        """
        Định tuyến gói tin 520-Byte Raw PCM 16kHz:
        - 0x00: AI Voice processing (bỏ qua ở router này)
        - 0xFF: Broadcast toàn bộ các màn hình
        - 0xFE: Riêng cho Web Admin Hub
        - 1..250: Unicast tới màn hình có intercom_id tương ứng
        """
        if len(packet) != 520:
            return

        # Magic Word: 0xA55A (0x5A, 0xA5 trong Little-Endian)
        if packet[0] != 0x5A or packet[1] != 0xA5:
            return

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
