from __future__ import annotations

from .binary_sensor import AdvanceMotionSensorPresence
from .const import EntryType
from .number import AdvanceMotionSensorTimeout
from .select import AdvanceMotionSensorMode
from .sensor import AdvanceMotionSensorState
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError


class AdvancedMotionSensorEntry:

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry: ConfigEntry = entry
        self._presence_sensor: AdvanceMotionSensorPresence | None = None
        self._timeout_number: AdvanceMotionSensorTimeout | None = None
        self._mode_select: AdvanceMotionSensorMode | None = None
        self._state_sensor: AdvanceMotionSensorState | None = None
        self._initialized: dict[EntryType, bool] = {
            EntryType.PRESENCE: False,
            EntryType.TIMEOUT: False,
            EntryType.MODE: False,
            EntryType.STATE: False,
        }

    async def async_added_to_hass(self, entry: EntryType) -> None:
        if self._initialized[entry]:
            raise HomeAssistantError(f"Entry ({entry}) is already initialized")

        self._initialized[entry] = True

        # check if all entries are initialized
        if all(self._initialized.values()):
            await self._presence_sensor.async_initialized()
            await self._timeout_number.async_initialized()
            await self._mode_select.async_initialized()
            await self._state_sensor.async_initialized()


    @property
    def entry_id(self) -> str:
        return self._entry.entry_id

    @property
    def name(self) -> str:
        return self._entry.title

    @property
    def sources(self) -> list[str]:
        return self._entry.data["sources"]

    @property
    def timeout(self) -> float:
        return self._entry.data["timeout"]
    
    @property
    def config_entry(self) -> ConfigEntry:
        return self._entry

    @property
    def state_sensor(self):
        return self._state_sensor

    @state_sensor.setter
    def state_sensor(self, value: AdvanceMotionSensorState):
        self._state_sensor = value

    @property
    def timeout_number(self) -> AdvanceMotionSensorTimeout:
        if self._timeout_number is None:
            raise HomeAssistantError("AdvanceMotionSensorTimeout is None")

        return self._timeout_number

    @timeout_number.setter
    def timeout_number(self, value: AdvanceMotionSensorTimeout):
        self._timeout_number = value
        
    @property
    def mode_select(self) -> AdvanceMotionSensorMode:
        return self._mode_select
    
    @mode_select.setter
    def mode_select(self, value: AdvanceMotionSensorMode):
        self._mode_select = value

    @property
    def presence_sensor(self) -> AdvanceMotionSensorPresence:
        return self._presence_sensor
    
    @presence_sensor.setter
    def presence_sensor(self, value: AdvanceMotionSensorPresence):
        self._presence_sensor = value
