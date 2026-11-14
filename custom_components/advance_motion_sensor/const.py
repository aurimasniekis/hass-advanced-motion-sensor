"""Constants for the Advance Motion Sensor integration."""
import logging

from enum import StrEnum

_LOGGER = logging.getLogger(__package__)

DOMAIN = "advance_motion_sensor"

MANUFACTURER = "Thruster Industries"


ATTR_TIMER_STATE = "timer_state"
ATTR_SOURCES = "sources"

EVENT_CLEARED = f"{DOMAIN}.cleared"
EVENT_DETECTED = f"{DOMAIN}.detected"
EVENT_TIMER = f"{DOMAIN}.timer"

EVENT_TIMER_FINISHED = f"{DOMAIN}.timer.finished"
EVENT_TIMER_CANCELLED = f"{DOMAIN}.timer.cancelled"
EVENT_TIMER_STARTED = f"{DOMAIN}.timer.started"

SERVICE_STOP_TIMER = "stop_timer"
SERVICE_MULTI_REGISTER = "register_multiple"


class EntryType(StrEnum):
    PRESENCE = "presence"
    TIMEOUT = "timeout"
    MODE = "mode"
    STATE = "state"
