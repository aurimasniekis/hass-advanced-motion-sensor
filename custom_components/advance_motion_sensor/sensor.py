from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Callable, TYPE_CHECKING

import homeassistant.util.dt as dt_util
from homeassistant.helpers import entity_registry as er, start, entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from .entity import AMSEntity

if TYPE_CHECKING:
    from .entry import AdvancedMotionSensorEntry

from .const import DOMAIN, ATTR_TIMER_STATE, ATTR_SOURCES, EVENT_DETECTED, EVENT_TIMER, EVENT_CLEARED, \
    EVENT_TIMER_FINISHED, EVENT_TIMER_CANCELLED, EVENT_TIMER_STARTED, EntryType, _LOGGER, SERVICE_STOP_TIMER
from .select import SensorModeOption
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from enum import StrEnum
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, callback, State, Event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_point_in_utc_time


# Timer attribute names, formerly imported from homeassistant.components.timer
# (no longer exported there in recent Home Assistant releases).
ATTR_DURATION = "duration"
ATTR_FINISHES_AT = "finishes_at"
ATTR_REMAINING = "remaining"


def _format_timedelta(delta: timedelta) -> str:
    """Format a timedelta as H:MM:SS, matching the timer integration."""
    total_seconds = delta.total_seconds()
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}:{int(minutes):02}:{int(seconds):02}"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Add sensors for passed config_entry in HA."""
    ams_entry: AdvancedMotionSensorEntry = hass.data[DOMAIN][entry.entry_id]

    entity = AdvanceMotionSensorState(
        hass,
        ams_entry
    )

    async_add_entities([entity])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_STOP_TIMER,
        {},
        "async_stop_timer",
    )


class SensorStateMode(StrEnum):
    SOME = "some"
    ALL = "all"
    NONE = "none"


class SensorStateOption(StrEnum):
    CLEAR = "clear"
    DETECTED = "detected"
    TIMER = "timer"


class SensorStateTimerOption(StrEnum):
    IDLE = "idle"
    ACTIVE = "active"


class AdvanceMotionSensorState(SensorEntity, AMSEntity):
    _attr_icon = "mdi:motion-sensor"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_translation_key = "advance_motion_sensor_state"
    _attr_should_poll = False

    _attr_options: list[SensorStateOption] = list(SensorStateOption)

    def __init__(self, hass: HomeAssistant, ams_entry: AdvancedMotionSensorEntry):
        super().__init__(ams_entry)

        self._hass = hass
        self._attr_unique_id = f"{self._entry_id}_state"
        self._attr_name = f"{self._name} State"
        self._is_overriden = False
        self._overriden_value: SensorStateOption = SensorStateOption.CLEAR

        self._attr_native_value: SensorStateOption = SensorStateOption.CLEAR
        self._attr_timer_value: SensorStateTimerOption = SensorStateTimerOption.IDLE

        self._attr_mode: SensorStateMode = SensorStateMode.SOME
        self._source_states: Dict[str, str] = {}

        self._attr_duration = timedelta(seconds=self._ams_entry.timeout)
        self._attr_remaining: timedelta | None = None
        self._attr_end: datetime | None = None
        self._listener: Callable[[], None] | None = None

        self._ams_entry.state_sensor = self

    @property
    def device_info(self) -> DeviceInfo | None:
        return {"identifiers": {(DOMAIN, self._entry_id)}}

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_DURATION: _format_timedelta(self._attr_duration),
            ATTR_TIMER_STATE: self._attr_timer_value
        }
        if self._attr_end is not None:
            attrs[ATTR_FINISHES_AT] = self._attr_end.isoformat()
        if self._attr_remaining is not None:
            attrs[ATTR_REMAINING] = _format_timedelta(self._attr_remaining)

        return attrs

    async def async_added_to_hass(self) -> None:
        await self._ams_entry.async_added_to_hass(EntryType.STATE)

    async def async_initialized(self) -> None:
        self.async_on_remove(start.async_at_start(self._hass, self._async_start))

    @callback
    def async_stop_timer(self):
        self._async_timer_cancel()

    async def _async_start(self, _: HomeAssistant | None = None) -> None:
        self._entity_registry = er.async_get(self._hass)
        self._async_start_sources_listener()
        self._async_start_mode_listener()
        self._async_start_timeout_listener()

    def _async_start_mode_listener(self, _=None) -> None:
        if mode := SensorModeOption.parse(self._ams_entry.mode_select.state or ""):
            self._mode_changed_listener(mode)
            self.async_schedule_update_ha_state()

        self.async_on_remove(
            async_track_state_change_event(self._hass, self._ams_entry.mode_select.entity_id,
                                           self._async_mode_changed_listener)
        )

    def _async_start_timeout_listener(self, _=None) -> None:
        if self._ams_entry.timeout_number.state:
            self._attr_duration = timedelta(seconds=int(self._ams_entry.timeout_number.state))
            self.async_schedule_update_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self._hass,
                self._ams_entry.timeout_number.entity_id,
                self._async_timeout_changed_listener
            )
        )

    @callback
    def _async_timeout_changed_listener(self, event: Event) -> None:
        new_state: State | None = event.data.get("new_state")
        if not new_state:
            return

        try:
            self._attr_duration = timedelta(seconds=int(float(new_state.state)))
        except ValueError:
            # unavailable / unknown: keep the current duration
            return

        self.async_schedule_update_ha_state()

    def _async_start_sources_listener(self):
        # Seed with the current source states so a source that is already "on"
        # at startup is seen without waiting for it to change.
        for entity_id in self._ams_entry.sources:
            if (state := self._hass.states.get(entity_id)) is not None:
                self._source_states[entity_id] = state.state

        self.async_on_remove(
            async_track_state_change_event(self._hass, self._ams_entry.sources, self._async_source_changed_listener)
        )

    @callback
    def _async_source_changed_listener(self, event: Event) -> None:
        entity_id: str = event.data["entity_id"]
        new_state: State | None = event.data.get("new_state")
        if not new_state:
            return

        self._source_states[entity_id] = new_state.state

        self._async_check_status()

    @callback
    def _async_mode_changed_listener(self, event: Event) -> None:
        new_state: State | None = event.data.get("new_state")
        if not new_state:
            return

        if mode := SensorModeOption.parse(new_state.state):
            self._mode_changed_listener(mode)

    def _mode_changed_listener(self, new_state: SensorModeOption) -> None:
        if new_state == SensorModeOption.AUTO:
            self._is_overriden = False
        elif new_state == SensorModeOption.CLEAR:
            self._is_overriden = True
            self._overriden_value = SensorStateOption.CLEAR
        elif new_state == SensorModeOption.DETECTED:
            self._is_overriden = True
            self._overriden_value = SensorStateOption.DETECTED
        else:
            _LOGGER.error("Unknown value received from mode state: %s", new_state)

        self._async_check_status()

    @property
    def native_value(self) -> SensorStateOption:
        if self._is_overriden:
            return self._overriden_value
        else:
            return self._attr_native_value

    def _async_check_status(self):
        if self._attr_native_value == SensorStateOption.CLEAR:
            if sources := self._check_sources():
                self._attr_native_value = SensorStateOption.DETECTED
                self._async_dispatch_event(EVENT_DETECTED, sources)

        elif self._attr_native_value == SensorStateOption.DETECTED:
            if not self._check_sources():
                self._attr_native_value = SensorStateOption.TIMER
                self._async_dispatch_event(EVENT_TIMER)
                self._async_timer_start()

        elif self._attr_native_value == SensorStateOption.TIMER:
            if sources := self._check_sources():
                self._attr_native_value = SensorStateOption.DETECTED
                self._async_dispatch_event(EVENT_DETECTED, sources)
                self._async_timer_cancel()
            else:
                if self._attr_timer_value == SensorStateTimerOption.IDLE:
                    self._attr_native_value = SensorStateOption.CLEAR
                    self._async_dispatch_event(EVENT_CLEARED)

        self.async_schedule_update_ha_state()

    def _check_sources(self) -> list[str] | None:
        affected_values = []

        if self._attr_mode == SensorStateMode.ALL:
            if all(value == "on" for value in self._source_states.values()):
                return list(self._source_states.keys())
            else:
                return None

        elif self._attr_mode == SensorStateMode.SOME:
            if any(value == "on" for value in self._source_states.values()):
                for key, value in self._source_states.items():
                    if value == "on":
                        affected_values.append(key)
                return affected_values
            else:
                return None

        elif self._attr_mode == SensorStateMode.NONE:
            if all(value != "on" for value in self._source_states.values()):
                return list(self._source_states.keys())
            else:
                return None

        return None

    def _async_timer_start(self, duration: timedelta | None = None):
        if self._listener:
            self._listener()
            self._listener = None

        self._attr_timer_value = SensorStateTimerOption.ACTIVE
        now = dt_util.utcnow().replace(microsecond=0)

        if duration:
            self._attr_remaining = self._attr_duration = duration
        elif not self._attr_remaining:
            self._attr_remaining = self._attr_duration

        self._attr_end = now + self._attr_remaining

        self._async_dispatch_timer_event(EVENT_TIMER_STARTED)

        self._listener = async_track_point_in_utc_time(
            self.hass, self._async_timer_finished, self._attr_end
        )

    @callback
    def _async_timer_finished(self, time):
        if self._attr_timer_value != SensorStateTimerOption.ACTIVE:
            return

        self._listener = None
        self._attr_end = None
        self._attr_remaining = None
        self._attr_timer_value = SensorStateTimerOption.IDLE

        self._async_check_status()
        self._async_dispatch_timer_event(EVENT_TIMER_FINISHED)

    def _async_timer_cancel(self):
        if self._listener:
            self._listener()
            self._listener = None

        self._attr_timer_value = SensorStateTimerOption.IDLE
        self._attr_end = None
        self._attr_remaining = None

        self._async_check_status()
        self._async_dispatch_timer_event(EVENT_TIMER_CANCELLED)

    def _async_dispatch_timer_event(self, event_name: str):
        self.hass.bus.async_fire(
            event_name,
            {
                ATTR_ENTITY_ID: self.entity_id
            }
        )

    def _async_dispatch_event(self, event_name: str, sources=None):
        if sources is None:
            sources = list()

        self.hass.bus.async_fire(
            event_name,
            {
                ATTR_ENTITY_ID: self.entity_id,
                ATTR_SOURCES: sources
            }
        )
