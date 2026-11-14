"""Tests for the advance_motion_sensor integration."""
from datetime import timedelta

import pytest
from homeassistant import config_entries
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

DOMAIN = "advance_motion_sensor"
M1 = "binary_sensor.motion_1"
M2 = "binary_sensor.motion_2"
STATE = "sensor.hallway_state"
PRESENCE = "binary_sensor.hallway_presence"
MODE = "select.hallway_mode"
TIMEOUT = "number.hallway_timer_duration"


async def _setup_entry(hass: HomeAssistant, timeout: int = 30) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hallway",
        data={"name": "Hallway", "timeout": timeout, "sources": [M1, M2]},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture(autouse=True)
def sources_off(hass: HomeAssistant) -> None:
    hass.states.async_set(M1, STATE_OFF)
    hass.states.async_set(M2, STATE_OFF)


async def test_config_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Hallway", "timeout": 30, "sources": [M1]}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Hallway"


async def test_config_flow_unknown_source(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Hallway", "timeout": 30, "sources": ["binary_sensor.missing"]},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_input"}


async def test_entities_created(hass: HomeAssistant) -> None:
    await _setup_entry(hass)
    assert hass.states.get(STATE).state == "clear"
    assert hass.states.get(PRESENCE).state == STATE_OFF
    assert hass.states.get(MODE).state == "auto"
    assert float(hass.states.get(TIMEOUT).state) == 30


async def test_source_already_on_at_startup(hass: HomeAssistant) -> None:
    hass.states.async_set(M1, STATE_ON)
    await _setup_entry(hass)

    assert hass.states.get(STATE).state == "detected"
    assert hass.states.get(PRESENCE).state == STATE_ON


async def test_detect_timer_clear(hass: HomeAssistant) -> None:
    await _setup_entry(hass, timeout=30)
    detected = async_capture_events(hass, f"{DOMAIN}.detected")
    cleared = async_capture_events(hass, f"{DOMAIN}.cleared")

    hass.states.async_set(M1, STATE_ON)
    await hass.async_block_till_done()
    assert hass.states.get(STATE).state == "detected"
    assert hass.states.get(PRESENCE).state == STATE_ON
    assert detected[0].data["sources"] == [M1]

    hass.states.async_set(M1, STATE_OFF)
    await hass.async_block_till_done()
    state = hass.states.get(STATE)
    assert state.state == "timer"
    assert state.attributes["timer_state"] == "active"
    assert state.attributes["duration"] == "0:00:30"
    assert hass.states.get(PRESENCE).state == STATE_ON

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()
    assert hass.states.get(STATE).state == "clear"
    assert hass.states.get(PRESENCE).state == STATE_OFF
    assert len(cleared) == 1


async def test_motion_during_timer_cancels_it(hass: HomeAssistant) -> None:
    await _setup_entry(hass)
    hass.states.async_set(M1, STATE_ON)
    hass.states.async_set(M1, STATE_OFF)
    await hass.async_block_till_done()
    assert hass.states.get(STATE).state == "timer"

    hass.states.async_set(M2, STATE_ON)
    await hass.async_block_till_done()
    assert hass.states.get(STATE).state == "detected"
    assert hass.states.get(STATE).attributes["timer_state"] == "idle"


async def test_stop_timer_service(hass: HomeAssistant) -> None:
    await _setup_entry(hass)
    hass.states.async_set(M1, STATE_ON)
    hass.states.async_set(M1, STATE_OFF)
    await hass.async_block_till_done()
    assert hass.states.get(STATE).state == "timer"

    await hass.services.async_call(DOMAIN, "stop_timer", {"entity_id": STATE}, blocking=True)
    assert hass.states.get(STATE).state == "clear"


async def test_mode_override(hass: HomeAssistant) -> None:
    await _setup_entry(hass)

    await hass.services.async_call(
        "select", "select_option", {"entity_id": MODE, "option": "detected"}, blocking=True
    )
    assert hass.states.get(MODE).state == "detected"
    assert hass.states.get(STATE).state == "detected"

    await hass.services.async_call(
        "select", "select_option", {"entity_id": MODE, "option": "auto"}, blocking=True
    )
    assert hass.states.get(STATE).state == "clear"


async def test_timeout_number(hass: HomeAssistant) -> None:
    await _setup_entry(hass)
    await hass.services.async_call(
        "number", "set_value", {"entity_id": TIMEOUT, "value": 90}, blocking=True
    )
    assert float(hass.states.get(TIMEOUT).state) == 90
    assert hass.states.get(STATE).attributes["duration"] == "0:01:30"


async def test_unavailable_helpers_are_ignored(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    await _setup_entry(hass)
    hass.states.async_set(MODE, STATE_UNAVAILABLE)
    hass.states.async_set(TIMEOUT, STATE_UNAVAILABLE)
    await hass.async_block_till_done()

    assert "ValueError" not in caplog.text
    assert hass.states.get(STATE).attributes["duration"] == "0:00:30"


async def test_register_multiple_without_entries(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, DOMAIN, {})
    response = await hass.services.async_call(
        DOMAIN,
        "register_multiple",
        {
            "entries": [
                {"name": "Kitchen", "timeout": 60, "sources": [M1]},
                {"name": "Broken", "timeout": 60, "sources": ["binary_sensor.missing"]},
            ]
        },
        blocking=True,
        return_response=True,
    )
    results = response["results"]
    assert results["Kitchen"]["success"] is True
    assert results["Broken"]["success"] is False
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_unload(hass: HomeAssistant) -> None:
    entry = await _setup_entry(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "register_multiple")
