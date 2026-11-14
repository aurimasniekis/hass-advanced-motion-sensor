from __future__ import annotations

from typing import Optional, Self
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

if TYPE_CHECKING:
    from .entry import AdvancedMotionSensorEntry

from .const import DOMAIN, EntryType, _LOGGER
from .entity import AMSEntity
from homeassistant.components.select import SelectEntity
from enum import StrEnum
from homeassistant.helpers.restore_state import RestoreEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    ams_entry: AdvancedMotionSensorEntry = hass.data[DOMAIN][entry.entry_id]

    entity = AdvanceMotionSensorMode(
        hass,
        ams_entry
    )

    async_add_entities([entity])


class SensorModeOption(StrEnum):
    AUTO = "auto"
    DETECTED = "detected"
    CLEAR = "clear"

    @classmethod
    def parse(cls, value: str) -> Optional[Self]:
        try:
            return SensorModeOption(value.lower())
        except ValueError:
            return None


class AdvanceMotionSensorMode(SelectEntity, RestoreEntity, AMSEntity):
    _attr_icon = "mdi:arrow-decision-auto"
    _attr_options: list[SensorModeOption] = list(SensorModeOption)
    _attr_translation_key = "advance_motion_sensor_mode"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, ams_entry: AdvancedMotionSensorEntry):
        super().__init__(ams_entry)

        self._hass = hass
        self._attr_unique_id = f"{self._entry_id}_mode"
        self._attr_name = f"{self._name} Mode"
        self._attr_current_option: SensorModeOption = SensorModeOption.AUTO

        self._ams_entry.mode_select = self

    async def async_added_to_hass(self) -> None:
        if last_data := await self.async_get_last_state():
            self._attr_current_option = SensorModeOption.parse(last_data.state) or SensorModeOption.AUTO

        await self._ams_entry.async_added_to_hass(EntryType.MODE)

    @property
    def device_info(self) -> DeviceInfo | None:
        return {"identifiers": {(DOMAIN, self._entry_id)}}

    async def async_select_option(self, option: str) -> None:
        value = SensorModeOption.parse(option)

        if value is None:
            _LOGGER.error("Invalid AdvanceMotionSensorMode option value provided \"%s\"", option)
            return

        self._attr_current_option = value
        self.async_write_ha_state()
