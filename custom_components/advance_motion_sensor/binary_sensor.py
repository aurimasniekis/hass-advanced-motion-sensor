from __future__ import annotations
from typing import TYPE_CHECKING

from homeassistant.helpers import start
from homeassistant.helpers.device_registry import DeviceInfo

if TYPE_CHECKING:
    from .entry import AdvancedMotionSensorEntry

from .const import DOMAIN, EntryType, _LOGGER
from .entity import AMSEntity
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, State, Event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Add sensors for passed config_entry in HA."""
    ams_entry: AdvancedMotionSensorEntry = hass.data[DOMAIN][entry.entry_id]

    entity = AdvanceMotionSensorPresence(
        hass,
        ams_entry
    )

    async_add_entities([entity])


class AdvanceMotionSensorPresence(BinarySensorEntity, AMSEntity):
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_icon = "mdi:motion-sensor"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, ams_entry: AdvancedMotionSensorEntry):
        super().__init__(ams_entry)

        self._hass = hass
        self._attr_unique_id = f"{self._ams_entry.entry_id}_presence"
        self._attr_name = f"{self._ams_entry.name} Presence"
        self._attr_is_on = False

        self._ams_entry.presence_sensor = self

    @property
    def device_info(self) -> DeviceInfo | None:
        return {"identifiers": {(DOMAIN, self._ams_entry.entry_id)}}

    async def async_added_to_hass(self) -> None:
        await self._ams_entry.async_added_to_hass(EntryType.PRESENCE)

    async def async_initialized(self) -> None:
        self.async_on_remove(start.async_at_started(self._hass, self._async_start))

    @callback
    async def _async_start(self, _: HomeAssistant | None = None) -> None:

        @callback
        def async_mode_changed_listener(event: Event) -> None:
            new_state: State | None = event.data.get("new_state")
            if new_state is None:
                return

            if new_state.state == "clear":
                self._attr_is_on = False
            elif new_state.state == "detected" or new_state.state == "timer":
                self._attr_is_on = True
            else:
                _LOGGER.error("Unknown value received from mode state: %s", new_state.state)

            self.async_schedule_update_ha_state()

        self.async_on_remove(
            async_track_state_change_event(self._hass, self._ams_entry.state_sensor.entity_id, async_mode_changed_listener)
        )
