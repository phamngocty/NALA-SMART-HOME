"""Config flow for NALA Smart Home Panel integration."""
import logging
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_HUB_HOST, CONF_HUB_PORT, DEFAULT_HOST, DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HUB_HOST, default=DEFAULT_HOST): str,
    vol.Required(CONF_HUB_PORT, default=DEFAULT_PORT): int,
})

async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validate the user input allows us to connect."""
    host = data[CONF_HUB_HOST]
    port = data[CONF_HUB_PORT]
    url = f"http://{host}:{port}/api/system/status"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return {"success": False, "error": "cannot_connect"}
                res_data = await resp.json()
                return {"success": True, "title": f"NALA Central Hub ({host})", "data": res_data}
    except Exception as e:
        _LOGGER.error("Cannot connect to NALA Hub at %s: %s", url, e)
        return {"success": False, "error": "cannot_connect"}

class NalaSmartPanelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NALA Smart Panel."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Check unique host
            await self.async_set_unique_id(f"{user_input[CONF_HUB_HOST]}:{user_input[CONF_HUB_PORT]}")
            self._abort_if_unique_id_configured()

            res = await validate_input(self.hass, user_input)
            if res.get("success"):
                return self.async_create_entry(
                    title=res.get("title", f"NALA Hub ({user_input[CONF_HUB_HOST]})"),
                    data=user_input,
                )
            else:
                errors["base"] = res.get("error", "cannot_connect")

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )
