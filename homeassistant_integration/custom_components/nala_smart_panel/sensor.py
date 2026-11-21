"""Sensors for NALA Smart Home Panels."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
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
    """Set up the sensor platform."""
    coordinator: NalaHubCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []
    for dev in coordinator.devices:
        code = dev.get("pairing_code", "UNKNOWN")
        entities.append(NalaPanelStatusSensor(coordinator, code))
        entities.append(NalaPanelIpSensor(coordinator, code))
        entities.append(NalaPanelRadarDistanceSensor(coordinator, code))
        entities.append(NalaPanelRadarStateSensor(coordinator, code))
        entities.append(NalaPanelRadarStaticEnergySensor(coordinator, code))
        entities.append(NalaPanelRadarMovingEnergySensor(coordinator, code))
        entities.append(NalaPanelRadarLightSensor(coordinator, code))
        entities.append(NalaPanelLivingContextSensor(coordinator, code))

    async_add_entities(entities)

class NalaPanelBaseEntity(CoordinatorEntity):
    """Base entity for NALA Panel."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator)
        self.pairing_code = pairing_code

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for Home Assistant device registry."""
        dev = next((d for d in self.coordinator.devices if d.get("pairing_code") == self.pairing_code), {})
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

class NalaPanelStatusSensor(NalaPanelBaseEntity, SensorEntity):
    """Trạng thái kết nối của màn hình gắn tường."""

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_status"
        self._attr_name = "Trạng Thái Màn Hình"
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
        self._attr_name = "Địa Chỉ IP"
        self._attr_icon = "mdi:ip-network"

    @property
    def native_value(self) -> str:
        dev = self._get_dev()
        return dev.get("ip", "0.0.0.0")

class NalaPanelRadarDistanceSensor(NalaPanelBaseEntity, SensorEntity):
    """Khoảng cách mục tiêu gần nhất từ Radar mmWave HLK-LD2410."""

    _attr_native_unit_of_measurement = "cm"
    _attr_icon = "mdi:map-marker-distance"

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_radar_distance"
        self._attr_name = "Radar Cự Ly"

    @property
    def native_value(self) -> int:
        dev = self._get_dev()
        return dev.get("radar", {}).get("dist_cm", 0)

class NalaPanelRadarStateSensor(NalaPanelBaseEntity, SensorEntity):
    """Trạng thái mục tiêu phát hiện (Vắng / Chuyển động / Tĩnh ngủ)."""

    _attr_icon = "mdi:account-clock"

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_radar_state"
        self._attr_name = "Radar Trạng Thái"

    @property
    def native_value(self) -> str:
        dev = self._get_dev()
        st = dev.get("radar", {}).get("state", 0)
        mapping = {
            0: "Phòng Vắng",
            1: "Đang Di Chuyển",
            2: "Tĩnh (Nằm/Ngủ)",
            3: "Di Chuyển & Tĩnh"
        }
        return mapping.get(st, "Không Rõ")

class NalaPanelRadarStaticEnergySensor(NalaPanelBaseEntity, SensorEntity):
    """Năng lượng vi động tĩnh / nhịp thở khi nằm ngủ từ Radar HLK-LD2410."""

    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:heart-pulse"

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_radar_static_energy"
        self._attr_name = "Radar Nhịp Thở Tĩnh"

    @property
    def native_value(self) -> int:
        dev = self._get_dev()
        return dev.get("radar", {}).get("st_eng", 0)

class NalaPanelRadarMovingEnergySensor(NalaPanelBaseEntity, SensorEntity):
    """Năng lượng chuyển động di chuyển trong phòng từ Radar HLK-LD2410."""

    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:motion"

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_radar_moving_energy"
        self._attr_name = "Radar Chuyển Động"

    @property
    def native_value(self) -> int:
        dev = self._get_dev()
        return dev.get("radar", {}).get("mv_eng", 0)

class NalaPanelRadarLightSensor(NalaPanelBaseEntity, SensorEntity):
    """Cường độ ánh sáng môi trường từ quang trở tích hợp trên Radar HLK-LD2410."""

    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "lx"
    _attr_icon = "mdi:brightness-6"

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_radar_light"
        self._attr_name = "Độ Sáng Môi Trường"

    @property
    def native_value(self) -> int:
        dev = self._get_dev()
        return dev.get("radar", {}).get("light", 0)


class NalaPanelLivingContextSensor(NalaPanelBaseEntity, SensorEntity):
    """Sensor báo Ngữ cảnh sống thông minh (Living Context: empty, active, approaching, deep_sleep, night_wakeup)."""

    _attr_icon = "mdi:home-clock"
    _attr_translation_key = "living_context"

    def __init__(self, coordinator: NalaHubCoordinator, pairing_code: str) -> None:
        super().__init__(coordinator, pairing_code)
        self._attr_unique_id = f"{DOMAIN}_{pairing_code}_living_context"
        self._attr_name = "Ngữ Cảnh Sống"

    @property
    def native_value(self) -> str:
        dev = self._get_dev()
        return dev.get("living_context", "empty")

    @property
    def extra_state_attributes(self) -> dict:
        dev = self._get_dev()
        radar = dev.get("radar", {})
        return {
            "distance_cm": radar.get("dist_cm", 0),
            "static_energy": radar.get("st_eng", 0),
            "moving_energy": radar.get("mv_eng", 0),
            "light_lux": radar.get("light", 0),
            "is_approaching": radar.get("is_approaching", False),
        }



