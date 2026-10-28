"""DataUpdateCoordinator for NALA Smart Panel."""
import asyncio
import logging
from datetime import timedelta
import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_HUB_HOST, CONF_HUB_PORT

_LOGGER = logging.getLogger(__name__)

class NalaHubCoordinator(DataUpdateCoordinator):
    """Class to manage fetching NALA Panel data from NAS Hub."""

    def __init__(self, hass: HomeAssistant, entry_data: dict) -> None:
        """Initialize the coordinator."""
        self.host = entry_data.get(CONF_HUB_HOST, "192.168.1.114")
        self.port = entry_data.get(CONF_HUB_PORT, 8765)
        self.base_url = f"http://{self.host}:{self.port}"
        self.devices: list[dict] = []
        self._ws_task = None
        self._stopped = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=15),
        )

    async def _async_update_data(self) -> list[dict]:
        """Fetch latest device list from NAS Hub REST API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/devices", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        raise UpdateFailed(f"HTTP error {resp.status} from NAS Hub")
                    devices = await resp.json()
                    self.devices = devices
                    return devices
        except Exception as err:
            raise UpdateFailed(f"Error communicating with NALA Hub: {err}") from err

    async def async_call_panel_action(self, pairing_code: str, action: str) -> bool:
        """Send action to a specific panel via Hub REST API."""
        url = f"{self.base_url}/api/devices/action"
        payload = {"pairing_code": pairing_code, "action": action}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status == 200
        except Exception as err:
            _LOGGER.error("Failed to send action '%s' to panel [%s]: %s", action, pairing_code, err)
            return False

    async def async_update_panel_settings(self, pairing_code: str, new_settings: dict) -> bool:
        """Update hardware settings (brightness, volume) for a panel."""
        dev = next((d for d in self.devices if d.get("pairing_code") == pairing_code), None)
        if not dev:
            return False

        merged_settings = dev.get("settings", {})
        merged_settings.update(new_settings)

        payload = {
            "pairing_code": pairing_code,
            "room_name": dev.get("room_name", "Phòng NALA"),
            "floor": dev.get("floor", "Tầng Trệt"),
            "buttons": dev.get("buttons", []),
            "entities": dev.get("entities", []),
            "settings": merged_settings
        }

        url = f"{self.base_url}/api/devices/pair"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        await self.async_request_refresh()
                        return True
                    return False
        except Exception as err:
            _LOGGER.error("Failed to update settings for panel [%s]: %s", pairing_code, err)
            return False
