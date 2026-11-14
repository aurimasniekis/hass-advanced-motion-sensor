import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback, HomeAssistant, ServiceCall, SupportsResponse, ServiceResponse
from .config_flow import STEP_USER_DATA_SCHEMA
from .const import DOMAIN, SERVICE_MULTI_REGISTER


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Create and register services for the Advanced Motion Sensor integration."""
    existing_services = hass.services.async_services().get(DOMAIN)
    if existing_services and SERVICE_MULTI_REGISTER in existing_services:
        # Integration-level services have already been added. Return.
        return

    async def _async_register_multiple(call: ServiceCall) -> ServiceResponse:
        results = {}

        for entry in call.data["entries"]:
            flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER},
                                                             data=entry)

            if "result" not in flow:
                results[entry["name"]] = {
                    "success": False,
                    "error": flow["errors"]
                }

            else:
                results[entry["name"]] = {
                    "success": True,
                    "entry_id": flow["result"].entry_id
                }

        return {
            "results": results,
        }

    hass.services.async_register(
        domain=DOMAIN,
        service=SERVICE_MULTI_REGISTER,
        service_func=_async_register_multiple,
        supports_response=SupportsResponse.ONLY,
        schema=vol.Schema({
            vol.Required("entries"): vol.All(
                list,
                [STEP_USER_DATA_SCHEMA]
            )
        }),
    )

