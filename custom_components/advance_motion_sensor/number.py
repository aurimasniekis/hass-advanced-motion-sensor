from __future__ import annotations
from typing import TYPE_CHECKING

from homeassistant.components.number import RestoreNumber, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

if TYPE_CHECKING:
    from .entry import AdvancedMotionSensorEntry

from .const import DOMAIN, EntryType
from .entity import AMSEntity
from homeassistant.const import EntityCategory


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Add sensors for passed config_entry in HA."""
    ams_entry: AdvancedMotionSensorEntry = hass.data[DOMAIN][entry.entry_id]

    entity = AdvanceMotionSensorTimeout(
        hass,
        ams_entry
    )

    async_add_entities([entity])


class AdvanceMotionSensorTimeout(RestoreNumber, AMSEntity):
    _attr_icon = "mdi:camera-timer"
    _attr_native_unit_of_measurement = "s"
    _attr_native_min_value = 1
    _attr_native_max_value = 86400
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, ams_entry: AdvancedMotionSensorEntry):
        super().__init__(ams_entry)

        self._hass = hass
        self._attr_unique_id = f"{self._entry_id}_timeout"
        self._attr_name = f"{self._name} Timer Duration"
        self._attr_native_value = ams_entry.timeout

        self._ams_entry.timeout_number = self

    async def async_added_to_hass(self) -> None:
        if last_number_data := await self.async_get_last_number_data():
            self._attr_native_value = last_number_data.native_value

        await self._ams_entry.async_added_to_hass(EntryType.TIMEOUT)

    @property
    def device_info(self) -> DeviceInfo | None:
        return {"identifiers": {(DOMAIN, self._entry_id)}}

    def set_native_value(self, value: float) -> None:
        self._attr_native_value = value
