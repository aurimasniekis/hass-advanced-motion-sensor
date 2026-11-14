from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entry import AdvancedMotionSensorEntry


class AMSEntity:

    def __init__(self, ams_entry: AdvancedMotionSensorEntry):
        self._ams_entry: AdvancedMotionSensorEntry = ams_entry

    async def async_initialized(self) -> None:
        pass

    @property
    def _entry_id(self) -> str:
        return self._ams_entry.entry_id

    @property
    def _name(self) -> str:
        return self._ams_entry.name
