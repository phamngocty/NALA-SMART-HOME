"""Binary Sensors for NALA Smart Home Panels (Radar mmWave HLK-LD2410)."""
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up the binary sensor platform."""
    coordinator: NalaHubCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []
    for dev in coordinator.devices:
        code = dev.get("pairing_code", "UNKNOWN")
        entities.append(NalaPanelRadarPresenceSensor(coordinator, code))
        entities.append(NalaPanelRadarApproachSensor(coordinator, code))
        entities.append(NalaPanelRadarSleepSensor(coordinator, code))
        entities.append(NalaPanelRadarMotionSensor(coordinator, code))

    async_add_entities(entities)

class NalaPanelBaseBinaryEntity(CoordinatorEntity):
    """Base binary entity for NALA Panel."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator)
        self.pairing_code = pairing_code

    @property
    def device_info(self) -> DeviceInfo:
        dev = self._get_dev()
        room = dev.get("room_name", f"Panel {self.pairing_code}")
        return DeviceInfo(
            identifiers={(DOMAIN, self.pairing_code)},
            name=f"{room}",
            manufacturer="NALA Smart Home",
            model=dev.get("model", "ES3C28P 2.8\" IPS"),
            sw_version=dev.get("firmware_version", "v3.6.2"),
            suggested_area=room,
        )

    def _get_dev(self) -> dict:
        return next((d for d in self.coordinator.devices if d.get("pairing_code") == self.pairing_code), {})

class NalaPanelRadarPresenceSensor(NalaPanelBaseBinaryEntity, BinarySensorEntity):
    """Phát hiện hiện diện người trong phòng bằng Radar mmWave HLK-LD2410."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_radar_presence"
        self._attr_name = "Radar Hiện Diện"
        self._attr_icon = "mdi:motion-sensor"

    @property
    def is_on(self) -> bool:
        dev = self._get_dev()
        radar = dev.get("radar", {})
        return bool(radar.get("presence", False))

    @property
    def extra_state_attributes(self) -> dict:
        dev = self._get_dev()
        radar = dev.get("radar", {})
        return {
            "distance_cm": radar.get("dist_cm", 0),
            "target_state": radar.get("state", 0),
            "moving_energy": radar.get("mv_eng", 0),
            "static_energy": radar.get("st_eng", 0),
            "approach_vector": radar.get("approach", False),
        }

class NalaPanelRadarApproachSensor(NalaPanelBaseBinaryEntity, BinarySensorEntity):
    """Phát hiện người đang tiến lại gần màn hình (<1.5m, gia tốc tiếp cận)."""

    _attr_device_class = BinarySensorDeviceClass.MOTION

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_radar_approach"
        self._attr_name = "Radar Tiếp Cận"
        self._attr_icon = "mdi:run-fast"

    @property
    def is_on(self) -> bool:
        dev = self._get_dev()
        radar = dev.get("radar", {})
        return bool(radar.get("approach", False))

class NalaPanelRadarSleepSensor(NalaPanelBaseBinaryEntity, BinarySensorEntity):
    """Phát hiện trạng thái nằm yên tĩnh / nhịp thở / ngủ bằng Radar."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_radar_sleep"
        self._attr_name = "Radar Đang Ngủ / Nghỉ Tĩnh"
        self._attr_icon = "mdi:bed"

    @property
    def is_on(self) -> bool:
        dev = self._get_dev()
        radar = dev.get("radar", {})
        state = radar.get("state", 0)
        st_eng = radar.get("st_eng", 0)
        return state in (2, 3) and st_eng >= 20

class NalaPanelRadarMotionSensor(NalaPanelBaseBinaryEntity, BinarySensorEntity):
    """Phát hiện cử động / bước đi di chuyển trong phòng bằng Radar."""

    _attr_device_class = BinarySensorDeviceClass.MOTION

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_radar_motion"
        self._attr_name = "Radar Đang Di Chuyển"
        self._attr_icon = "mdi:walk"

    @property
    def is_on(self) -> bool:
        dev = self._get_dev()
        radar = dev.get("radar", {})
        state = radar.get("state", 0)
        mv_eng = radar.get("mv_eng", 0)
        return state in (1, 3) and mv_eng >= 25
