"""Number entities for NALA Smart Home Panel hardware controls."""
from homeassistant.components.number import NumberEntity, NumberMode
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
    """Set up the number platform."""
    coordinator: NalaHubCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[NumberEntity] = []
    for dev in coordinator.devices:
        code = dev.get("pairing_code", "UNKNOWN")
        entities.append(NalaPanelBrightnessNumber(coordinator, code))
        entities.append(NalaPanelVolumeNumber(coordinator, code))

    async_add_entities(entities)

class NalaPanelBaseNumber(CoordinatorEntity, NumberEntity):
    """Base number entity for NALA Panel."""

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

    def _get_dev(self) -> dict:
        return next((d for d in self.coordinator.devices if d.get("pairing_code") == self.pairing_code), {})

class NalaPanelBrightnessNumber(NalaPanelBaseNumber):
    """Điều chỉnh độ sáng màn hình (0 - 100%)."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_brightness"
        self._attr_name = "Độ Sáng Màn Hình"
        self._attr_icon = "mdi:brightness-6"
        self._attr_native_min_value = 10
        self._attr_native_max_value = 100
        self._attr_native_step = 5
        self._attr_mode = NumberMode.SLIDER

    @property
    def native_value(self) -> float:
        dev = self._get_dev()
        settings = dev.get("settings", {})
        return float(settings.get("brightness", 90))

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_update_panel_settings(
            self.pairing_code, {"brightness": int(value)}
        )

class NalaPanelVolumeNumber(NalaPanelBaseNumber):
    """Điều chỉnh âm lượng loa đàm thoại (0 - 100%)."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_volume"
        self._attr_name = "Âm Lượng Loa"
        self._attr_icon = "mdi:volume-high"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 5
        self._attr_mode = NumberMode.SLIDER

    @property
    def native_value(self) -> float:
        dev = self._get_dev()
        settings = dev.get("settings", {})
        return float(settings.get("volume", 80))

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_update_panel_settings(
            self.pairing_code, {"volume": int(value)}
        )
