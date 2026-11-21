"""Switch entities for NALA Smart Home Panel hardware controls."""
from homeassistant.components.switch import SwitchEntity
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
    """Set up the switch platform."""
    coordinator: NalaHubCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SwitchEntity] = []
    for dev in coordinator.devices:
        code = dev.get("pairing_code", "UNKNOWN")
        entities.append(NalaPanelRadarEnabledSwitch(coordinator, code))
        entities.append(NalaPanelRadarWaveHangupSwitch(coordinator, code))

    async_add_entities(entities)

class NalaPanelBaseSwitch(CoordinatorEntity, SwitchEntity):
    """Base switch entity for NALA Panel."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator)
        self.pairing_code = pairing_code

    @property
    def device_info(self) -> DeviceInfo:
        dev = next((d for d in self.coordinator.devices if d.get("pairing_code") == self.pairing_code), {})
        room = dev.get("room_name", f"Panel {self.pairing_code}")
        return DeviceInfo(
            identifiers={(DOMAIN, self.pairing_code)},
            name=f"{room}",
            manufacturer="NALA Smart Home",
            model=dev.get("model", "ES3C28P 2.8\" IPS"),
            sw_version=dev.get("firmware_version", "v3.6.3"),
            suggested_area=room,
        )

    def _get_dev(self) -> dict:
        return next((d for d in self.coordinator.devices if d.get("pairing_code") == self.pairing_code), {})

class NalaPanelRadarEnabledSwitch(NalaPanelBaseSwitch):
    """Bật / Tắt Radar mmWave HLK-LD2410."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_radar_enabled"
        self._attr_name = "Bật Radar LD2410"
        self._attr_icon = "mdi:radar"

    @property
    def is_on(self) -> bool:
        dev = self._get_dev()
        return bool(dev.get("settings", {}).get("radar_enabled", True))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_update_panel_settings(
            self.pairing_code, {"radar_enabled": True}
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_update_panel_settings(
            self.pairing_code, {"radar_enabled": False}
        )

class NalaPanelRadarWaveHangupSwitch(NalaPanelBaseSwitch):
    """Bật / Tắt cử chỉ vẫy tay cúp máy (<30cm)."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_radar_wave_hangup"
        self._attr_name = "Cử Chỉ Vẫy Tay Cúp Máy"
        self._attr_icon = "mdi:hand-wave"

    @property
    def is_on(self) -> bool:
        dev = self._get_dev()
        return bool(dev.get("settings", {}).get("radar_wave_hangup", True))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_update_panel_settings(
            self.pairing_code, {"radar_wave_hangup": True}
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_update_panel_settings(
            self.pairing_code, {"radar_wave_hangup": False}
        )
