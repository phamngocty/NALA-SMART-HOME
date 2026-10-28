"""
NALA SMART HOME - HOME ASSISTANT BRIDGE
Handles bidirectional WebSocket connection to Home Assistant.
Executes local smart home intents with sub-200ms latency and broadcasts state changes.
Pulls Areas (Phòng), Floors (Tầng), and Entities directly from Home Assistant.
"""

import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Callable, Any, Optional

logger = logging.getLogger("HABridge")

class HomeAssistantBridge:
    def __init__(self, ws_url: str, access_token: str):
        self.ws_url = ws_url
        self.token = access_token
        self.ws = None
        self.msg_id = 0
        self.pending_requests: Dict[int, str] = {}
        self.authenticated = False
        self.states: Dict[str, dict] = {}
        self.floors: Dict[str, dict] = {}
        self.areas: Dict[str, dict] = {}
        self.devices: Dict[str, dict] = {}
        self.entity_registry: Dict[str, dict] = {}
        self.state_listeners: List[Callable[[str, str, dict], Any]] = []

    def _next_id(self) -> int:
        self.msg_id += 1
        return self.msg_id

    def add_state_listener(self, callback: Callable[[str, str, dict], Any]):
        """Thêm hàm callback nhận thông báo khi có thực thể HA thay đổi trạng thái."""
        self.state_listeners.append(callback)

    async def connect(self):
        """Duy trì kết nối WebSocket liên tục tới Home Assistant (auto-reconnect)."""
        while True:
            if not self.token:
                logger.info("Home Assistant token is not set yet. Waiting for configuration via Web Admin...")
                await asyncio.sleep(5)
                continue

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(self.ws_url) as ws:
                        self.ws = ws
                        logger.info("Connected to Home Assistant at %s", self.ws_url)
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await self._handle_message(json.loads(msg.data))
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except Exception as e:
                logger.warning("Home Assistant connection error: %s. Retrying in 5s...", e)
                self.authenticated = False
                await asyncio.sleep(5)

    async def _handle_message(self, data: dict):
        try:
            msg_type = data.get("type")
            if msg_type == "auth_required":
                await self.ws.send_json({"type": "auth", "access_token": self.token})
            elif msg_type == "auth_ok":
                self.authenticated = True
                logger.info("Successfully authenticated with Home Assistant")
                await self._subscribe_events()
                await self._fetch_all_states()
                await self._fetch_registries()
            elif msg_type == "auth_invalid":
                self.authenticated = False
                logger.error("Home Assistant authentication failed: %s", data.get("message"))
            elif msg_type == "result":
                req_id = data.get("id")
                req_type = self.pending_requests.pop(req_id, None)
                if data.get("success"):
                    res = data.get("result")
                    if req_type == "states" and isinstance(res, list):
                        for item in res:
                            if isinstance(item, dict) and "entity_id" in item:
                                self.states[item["entity_id"]] = item
                        logger.info("Fetched %d states from Home Assistant", len(self.states))
                    elif req_type == "floors" and isinstance(res, list):
                        self.floors = {f["floor_id"]: f for f in res if isinstance(f, dict) and "floor_id" in f}
                        logger.info("Fetched %d floors from Home Assistant", len(self.floors))
                    elif req_type == "areas" and isinstance(res, list):
                        self.areas = {a["area_id"]: a for a in res if isinstance(a, dict) and "area_id" in a}
                        logger.info("Fetched %d areas from Home Assistant", len(self.areas))
                    elif req_type == "device_registry" and isinstance(res, list):
                        self.devices = {d["id"]: d for d in res if isinstance(d, dict) and "id" in d}
                        logger.info("Fetched %d devices from Home Assistant", len(self.devices))
                    elif req_type == "entity_registry" and isinstance(res, list):
                        self.entity_registry = {e["entity_id"]: e for e in res if isinstance(e, dict) and "entity_id" in e}
                        logger.info("Fetched %d registry entities from Home Assistant", len(self.entity_registry))
                else:
                    logger.warning("HA request %s (%s) failed: %s", req_id, req_type, data.get("error"))
            elif msg_type == "event":
                event = data.get("event") or {}
                if event.get("event_type") == "state_changed":
                    event_data = event.get("data") or {}
                    entity_id = event_data.get("entity_id")
                    new_state_obj = event_data.get("new_state")
                    if entity_id and new_state_obj:
                        state_val = new_state_obj.get("state", "")
                        self.states[entity_id] = new_state_obj
                        for listener in self.state_listeners:
                            try:
                                if asyncio.iscoroutinefunction(listener):
                                    asyncio.create_task(listener(entity_id, state_val, new_state_obj))
                                else:
                                    listener(entity_id, state_val, new_state_obj)
                            except Exception as ex:
                                logger.error("Error invoking state listener: %s", ex)
        except Exception as e:
            logger.exception("Error handling HA message: %s", e)

    async def _subscribe_events(self):
        req_id = self._next_id()
        self.pending_requests[req_id] = "subscribe_events"
        await self.ws.send_json({
            "id": req_id,
            "type": "subscribe_events",
            "event_type": "state_changed"
        })

    async def _fetch_all_states(self):
        req_id = self._next_id()
        self.pending_requests[req_id] = "states"
        await self.ws.send_json({
            "id": req_id,
            "type": "get_states"
        })

    async def _fetch_registries(self):
        """Lấy danh sách Tầng, Phòng và Registry để ánh xạ vị trí màn hình."""
        try:
            req_id_fl = self._next_id()
            self.pending_requests[req_id_fl] = "floors"
            await self.ws.send_json({"id": req_id_fl, "type": "config/floor_registry/list"})

            req_id_ar = self._next_id()
            self.pending_requests[req_id_ar] = "areas"
            await self.ws.send_json({"id": req_id_ar, "type": "config/area_registry/list"})

            req_id_dev = self._next_id()
            self.pending_requests[req_id_dev] = "device_registry"
            await self.ws.send_json({"id": req_id_dev, "type": "config/device_registry/list"})

            req_id_ent = self._next_id()
            self.pending_requests[req_id_ent] = "entity_registry"
            await self.ws.send_json({"id": req_id_ent, "type": "config/entity_registry/list"})
        except Exception as e:
            logger.error("Failed to fetch HA registries: %s", e)

    def get_areas_list(self) -> List[dict]:
        """Trả về danh sách phòng kèm vị trí tầng tương ứng từ Home Assistant."""
        result = []
        for aid, a in self.areas.items():
            fl_id = a.get("floor_id")
            fl_obj = self.floors.get(fl_id, {})
            fl_name = fl_obj.get("name", fl_id or "")
            result.append({
                "area_id": aid,
                "name": a.get("name", aid),
                "floor_id": fl_id,
                "floor_name": fl_name,
                "icon": a.get("icon")
            })
        return sorted(result, key=lambda x: (x.get("floor_name") or "", x.get("name") or ""))

    def get_floors_list(self) -> List[dict]:
        """Trả về danh sách tầng từ Home Assistant."""
        return list(self.floors.values())

    def get_entities_list(self) -> List[dict]:
        """Trả về danh sách thực thể kèm thông tin Phòng (Area) và Tầng (Floor) từ HA."""
        if self.states:
            entities = []
            for eid, obj in self.states.items():
                domain = eid.split(".")[0]
                if domain in ("light", "switch", "fan", "climate", "cover", "scene", "input_boolean", "media_player"):
                    attrs = obj.get("attributes", {})
                    friendly_name = attrs.get("friendly_name", eid)
                    reg_entry = self.entity_registry.get(eid, {})

                    # Tìm area_id: ưu tiên từ entity_registry, nếu trống thì tìm qua device_registry
                    area_id = reg_entry.get("area_id")
                    dev_id = reg_entry.get("device_id")
                    if not area_id and dev_id:
                        area_id = self.devices.get(dev_id, {}).get("area_id")
                    if not area_id:
                        for aid in self.areas.keys():
                            if aid and aid in eid:
                                area_id = aid
                                break
                    area_id = area_id or ""

                    area_obj = self.areas.get(area_id, {})
                    area_name = area_obj.get("name", "")
                    floor_id = area_obj.get("floor_id", "")
                    floor_obj = self.floors.get(floor_id, {})
                    floor_name = floor_obj.get("name", "")

                    entities.append({
                        "entity_id": eid,
                        "name": friendly_name,
                        "domain": domain,
                        "state": obj.get("state", "off"),
                        "area_id": area_id,
                        "area_name": area_name,
                        "floor_id": floor_id,
                        "floor_name": floor_name
                    })
            return entities

        # Mock fallback nếu chưa kết nối token HA
        return [
            {"entity_id": "light.phong_khach", "name": "Đèn Phòng Khách", "domain": "light", "state": "off", "area_id": "phong_khach"},
            {"entity_id": "fan.phong_khach", "name": "Quạt Phòng Khách", "domain": "fan", "state": "off", "area_id": "phong_khach"},
            {"entity_id": "climate.150633094640317_climate", "name": "Máy lạnh phòng ngủ tỷ", "domain": "climate", "state": "off", "area_id": "phong_ngu_ty"}
        ]

    async def reconfigure(self, new_url: str, new_token: str):
        """Cập nhật URL & Token mới và ngắt socket cũ để kết nối lại ngay lập tức."""
        self.ws_url = new_url.strip()
        self.token = new_token.strip()
        self.authenticated = False
        if self.ws and not self.ws.closed:
            await self.ws.close()
        logger.info("HA Bridge reconfigured with new credentials. Reconnecting...")

    async def call_service(self, domain: str, service: str, entity_id: str, service_data: Optional[dict] = None) -> bool:
        """Thực thi lệnh điều khiển thiết bị với độ trễ < 200ms."""
        if domain == "climate":
            cur_state = self.states.get(entity_id, {}).get("state", "off")
            if service == "toggle":
                if cur_state == "off":
                    service = "set_hvac_mode"
                    service_data = {"hvac_mode": "cool"}
                else:
                    service = "set_hvac_mode"
                    service_data = {"hvac_mode": "off"}
        elif domain == "scene":
            service = "turn_on"
        elif domain == "cover" and service == "toggle":
            cur_state = self.states.get(entity_id, {}).get("state", "open")
            service = "close_cover" if cur_state == "open" else "open_cover"

        if not self.authenticated or not self.ws:
            logger.info("[MOCK/STANDALONE] HA Call: %s.%s on %s", domain, service, entity_id)
            current = self.states.get(entity_id, {}).get("state", "off")
            new_state = "on" if (service in ("turn_on", "cool") or (service == "toggle" and current == "off")) else "off"
            self.states[entity_id] = {"state": new_state, "attributes": {"friendly_name": entity_id}}
            for listener in self.state_listeners:
                try:
                    if asyncio.iscoroutinefunction(listener):
                        asyncio.create_task(listener(entity_id, new_state, self.states[entity_id]))
                    else:
                        listener(entity_id, new_state, self.states[entity_id])
                except Exception as ex:
                    logger.error("Error invoking state listener: %s", ex)
            return True

        req_id = self._next_id()
        payload = {
            "id": req_id,
            "type": "call_service",
            "domain": domain,
            "service": service,
            "target": {"entity_id": entity_id}
        }
        if service_data:
            payload["service_data"] = service_data

        try:
            await self.ws.send_json(payload)
            logger.info("Called HA Service: %s.%s on %s (data=%s)", domain, service, entity_id, service_data)
            return True
        except Exception as e:
            logger.error("Error calling HA service: %s", e)
            return False
