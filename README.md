# Advanced Motion Sensor

[![Validate](https://github.com/aurimasniekis/hass-advanced-motion-sensor/actions/workflows/validate.yml/badge.svg)](https://github.com/aurimasniekis/hass-advanced-motion-sensor/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant integration that **combines one or more motion sensors into a single presence
sensor with an off-delay timer**, a manual override, and events you can automate on.

```
any source on ──► detected ──(all sources off)──► timer ──(timer ends)──► clear
                     ▲                              │
                     └──────(motion again)──────────┘
```

## Installation

### HACS (recommended)

1. In HACS, open the menu (⋮) → **Custom repositories**.
2. Add `https://github.com/aurimasniekis/hass-advanced-motion-sensor` with type **Integration**.
3. Install **Advanced Motion Sensor** and restart Home Assistant.

### Manual

Copy `custom_components/advance_motion_sensor` into your Home Assistant `config/custom_components/`
folder and restart Home Assistant.

> The integration's domain is `advance_motion_sensor` (without the "d"). It is kept that way so
> existing installations keep their entries and entities.

## Setup

**Settings → Devices & services → Add integration → Advanced Motion Sensor**, then enter:

| Field          | Description                                                     |
| -------------- | --------------------------------------------------------------- |
| Name           | Used for the device and entity names.                           |
| Timer Duration | Seconds to wait after the last motion before clearing.          |
| Motion Sources | One or more `binary_sensor` entities (motion, occupancy, door). |

## Entities

For a sensor named **Hallway**:

| Entity                            | Description                                                                                                                                         |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sensor.hallway_state`            | `clear`, `detected` or `timer`. Attributes: `duration`, `timer_state` (`idle`/`active`), and while the timer runs `finishes_at` and `remaining`.     |
| `binary_sensor.hallway_presence`  | Occupancy sensor: on while `detected` or `timer`, off when `clear`. Use this one in automations.                                                    |
| `number.hallway_timer_duration`   | Timer duration in seconds. Changes apply to the next timer and survive restarts.                                                                    |
| `select.hallway_mode`             | `auto` (follow the sources), or force `detected` / `clear`.                                                                                         |

## How it works

- **Detected**: at least one source is `on`. Sources that are already on at startup are picked up
  immediately.
- **Timer**: all sources went off. The timer runs for the configured duration.
- **Clear**: the timer finished.
- Motion during the timer cancels it and goes back to **detected**.
- Setting the mode to `detected` or `clear` overrides the reported state until you set it back to
  `auto`.

## Events

Every event includes `entity_id` (the state sensor).

| Event                                    | Fired when                          | Extra data                                   |
| ---------------------------------------- | ----------------------------------- | -------------------------------------------- |
| `advance_motion_sensor.detected`         | the state becomes `detected`        | `sources`: the sources that are on           |
| `advance_motion_sensor.timer`            | the state becomes `timer`           | `sources` (empty list)                       |
| `advance_motion_sensor.cleared`          | the state becomes `clear`           | `sources` (empty list)                       |
| `advance_motion_sensor.timer.started`    | the timer starts                    |                                              |
| `advance_motion_sensor.timer.finished`   | the timer runs out                  |                                              |
| `advance_motion_sensor.timer.cancelled`  | the timer is cancelled or stopped   |                                              |

## Services

### `advance_motion_sensor.stop_timer`

Stops a running timer immediately, which clears the sensor.

```yaml
action: advance_motion_sensor.stop_timer
target:
  entity_id: sensor.hallway_state
```

### `advance_motion_sensor.register_multiple`

Creates several sensors at once and returns the result for each one.

```yaml
action: advance_motion_sensor.register_multiple
data:
  entries:
    - name: Hallway
      timeout: 120
      sources:
        - binary_sensor.hallway_motion_1
        - binary_sensor.hallway_motion_2
    - name: Kitchen
      timeout: 60
      sources:
        - binary_sensor.kitchen_motion
response_variable: result
```

## Moving from a manual install

HACS installs into the same `custom_components/advance_motion_sensor` folder, so existing entries,
entities and automations keep working. Delete the old folder (or let HACS overwrite it), install
through HACS, and restart.

## Debug logging

```yaml
logger:
  logs:
    custom_components.advance_motion_sensor: debug
```

## Development

Tests run against a real Home Assistant instance with
[pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component):

```sh
pip install -r requirements_test.txt
python -m pytest
```

## License

[MIT](LICENSE)
