"""The Advance Motion Sensor integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_platform
from .const import DOMAIN, SERVICE_STOP_TIMER, MANUFACTURER
from .entry import AdvancedMotionSensorEntry
from .services import async_setup_services, async_unload_services
from homeassistant import config_entries

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.NUMBER, Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Advance Motion Sensor from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    ams_entry = hass.data[DOMAIN][entry.entry_id] = AdvancedMotionSensorEntry(entry)

    _async_get_or_create_device_in_registry(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    data = hass.data[DOMAIN][entry.entry_id]

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    async_unload_services(hass)

    return unload_ok


@callback
def _async_get_or_create_device_in_registry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> None:
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=MANUFACTURER,
        name=entry.title
    )
