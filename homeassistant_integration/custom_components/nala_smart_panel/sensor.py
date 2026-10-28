"""Sensors for NALA Smart Home Panels."""
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NalaHubCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: NalaHubCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []
    for dev in coordinator.devices:
        code = dev.get("pairing_code", "UNKNOWN")
        entities.append(NalaPanelStatusSensor(coordinator, code))
        entities.append(NalaPanelIpSensor(coordinator, code))

    async_add_entities(entities)

class NalaPanelBaseEntity(CoordinatorEntity):
    """Base entity for NALA Panel."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator)
        self.pairing_code = pairing_code

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for Home Assistant device registry."""
        dev = next((d for d in self.coordinator.devices if d.get("pairing_code") == self.pairing_code), {})
        room = dev.get("room_name", f"Màn Hình [{self.pairing_code}]")
        return DeviceInfo(
            identifiers={(DOMAIN, self.pairing_code)},
            name=f"NALA Panel {self.pairing_code} ({room})",
            manufacturer="NALA Smart Home",
            model=dev.get("model", "ES3C28P 2.8\" IPS"),
            sw_version="v2.5.0-HA-FloorRegistry",
            suggested_area=dev.get("room_name"),
        )

    def _get_dev(self) -> dict:
        return next((d for d in self.coordinator.devices if d.get("pairing_code") == self.pairing_code), {})

class NalaPanelStatusSensor(NalaPanelBaseEntity, SensorEntity):
    """Trạng thái kết nối của màn hình gắn tường."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_status"
        self._attr_name = f"Trạng Thái Màn Hình"
        self._attr_icon = "mdi:tablet"

    @property
    def native_value(self) -> str:
        dev = self._get_dev()
        return "Online" if dev.get("online") else "Offline"

    @property
    def extra_state_attributes(self) -> dict:
        dev = self._get_dev()
        return {
            "pairing_code": dev.get("pairing_code"),
            "mac": dev.get("mac"),
            "ip": dev.get("ip"),
            "room_name": dev.get("room_name"),
            "floor": dev.get("floor"),
            "buttons_count": len(dev.get("buttons", [])),
            "paired": dev.get("is_paired", False),
        }

class NalaPanelIpSensor(NalaPanelBaseEntity, SensorEntity):
    """Địa chỉ IP nội mạng của màn hình."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_ip"
        self._attr_name = f"Địa Chỉ IP"
        self._attr_icon = "mdi:ip-network"

    @property
    def native_value(self) -> str:
        dev = self._get_dev()
        return dev.get("ip", "0.0.0.0")
