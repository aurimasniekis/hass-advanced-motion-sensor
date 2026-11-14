"""Config flow for Advance Motion Sensor integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, _LOGGER
from homeassistant.helpers import selector
from homeassistant.helpers.selector import NumberSelectorMode

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("name"): selector.TextSelector(),
        vol.Required("timeout", default=120): selector.NumberSelector(
            selector.NumberSelectorConfig(unit_of_measurement="seconds", mode=NumberSelectorMode.BOX)
        ),
        vol.Required("sources"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN, multiple=True)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    for entity_id in data["sources"]:
        if entity_id not in hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN):
            raise vol.Invalid(f"The entity {entity_id} does not exist in Home Assistant")

    # Return info that you want to store in the config entry.
    return {"title": data["name"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Advance Motion Sensor."""

    VERSION = 1

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except vol.Invalid as err:
                _LOGGER.error(err)
                errors["base"] = "invalid_input"
                errors["message"] = str(err)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
