"""Action Buttons for NALA Smart Home Panels."""
from homeassistant.components.button import ButtonEntity
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
    """Set up the button platform."""
    coordinator: NalaHubCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ButtonEntity] = []
    for dev in coordinator.devices:
        code = dev.get("pairing_code", "UNKNOWN")
        entities.append(NalaPanelSyncButton(coordinator, code))
        entities.append(NalaPanelEnterApButton(coordinator, code))
        entities.append(NalaPanelRebootButton(coordinator, code))

    async_add_entities(entities)

class NalaPanelBaseButton(CoordinatorEntity, ButtonEntity):
    """Base button for NALA Panel."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator)
        self.pairing_code = pairing_code

    @property
    def device_info(self) -> DeviceInfo:
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

class NalaPanelSyncButton(NalaPanelBaseButton):
    """Nút bấm gửi lệnh đồng bộ cấu hình tức thời xuống màn hình qua WebSocket."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_sync"
        self._attr_name = "Đồng Bộ Màn Hình"
        self._attr_icon = "mdi:sync"

    async def async_press(self) -> None:
        """Trigger sync action."""
        await self.coordinator.async_call_panel_action(self.pairing_code, "sync")

class NalaPanelEnterApButton(NalaPanelBaseButton):
    """Nút bấm đưa màn hình về chế độ phát WiFi Soft-AP (192.168.4.1)."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_enter_ap"
        self._attr_name = "Chuyển Về AP Cấu Hình (192.168.4.1)"
        self._attr_icon = "mdi:access-point"

    async def async_press(self) -> None:
        """Trigger enter_ap action."""
        await self.coordinator.async_call_panel_action(self.pairing_code, "enter_ap")

class NalaPanelRebootButton(NalaPanelBaseButton):
    """Nút bấm khởi động lại màn hình từ xa."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_reboot"
        self._attr_name = "Khởi Động Lại Màn Hình"
        self._attr_icon = "mdi:restart"

    async def async_press(self) -> None:
        """Trigger reboot action."""
        await self.coordinator.async_call_panel_action(self.pairing_code, "reboot")
