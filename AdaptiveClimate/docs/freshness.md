# Input freshness and held event-driven states

This change starts from `4982bcb738e94444ac305adaf6278f61e637e5c1`.
The complete `thermal_model.h` and its existing numerical tests remain unchanged,
including three-parameter RLS, coefficient bounds, radiator lag, five-minute
observations, 24 accepted samples and forecast horizons. Input handling is in
`input_policy.h` and the ESPHome wrapper. No thermostat files or controls change.

## Exact changes for your current thermostaat.yaml

Your latest configuration already has **both** observer devices and models.
Keep all four devices, their areas, `api`, network settings and
`packages.thermostat_package` exactly as they are. Use
[thermostaat_freshness.yaml](../examples/thermostaat_freshness.yaml) as a merge
snippet: update the existing external-component source ref and replace only the
existing `packages.observer` entry. Both refs become
`feature/adaptive-climate-freshness`; pin the same reviewed commit for production.

For each of the two existing `ObserveRoom.yaml` entries, add these vars:

```yaml
          observer_require_api_connection: "true"
          observer_valve_command_scale: "100.0"
          observer_input_freshness:
            room_temperature:
              mode: event_driven
              stale_after: 15min
            outdoor_temperature:
              mode: event_driven
              stale_after: 15min
            valve_command:
              mode: strict
              stale_after: 1min
            supply_temperature:
              mode: strict
              stale_after: 15min
```

Keep `observer_stale_after: 15min`, both model IDs/names, nested device vars and
all seven input IDs. In particular your latest valve inputs are `pid_output_stijn`
and `pid_output_nick`. ClimateDevice publishes their **raw** command in 0–1 and
then multiplies by 100 in a filter. The new explicit scale converts that raw value
to percent **only inside the observer**. Default scale is 1 for already-percent
raw inputs, including `climate_stijn_valve_opening_degree`. Do not use scale 100
with an input already publishing raw percent. This fixes units at the input
boundary, without changing model math, PID outputs or valve commands.

Room and outdoor HA readings are explicitly held between events. The local PID
command publishes every five seconds in your configuration, so a one-minute
deadline is appropriate. Measured boiler supply remains strict: a missing
OpenTherm response must not silently become indefinitely valid. If supply really
has event-only semantics, verify that source contract before changing its policy.

## Policy contract

The component's optional `input_freshness` mapping accepts separate entries for
`room_temperature`, `outdoor_temperature`, `valve_command`, `supply_temperature`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `mode` | `strict` | `strict` expires; `event_driven` permits holding valid state |
| `stale_after` | Component `stale_after` (15min) | 1–60min, independently overridden per input |
| `availability` | Unconfigured | Optional ESPHome binary-sensor ID; known true required |

In strict mode, age greater than the deadline blocks learning. In event-driven
mode, the same deadline changes the diagnostic to `held_unconfirmed` but does
not block learning. A never-received, NaN, infinite, out-of-range or known-unhealthy
input blocks both modes. Invalid publications replace the usable value; the
observer does not fall back to a previously valid value after a known failure.
Recovery requires a valid raw publication (and a true health gate if configured).
Health failures do not reset model coefficients, but do break the training
interval so it cannot span the outage. Window and DHW protections remain intact.

Use an existing trustworthy health sensor when available, for example:

```yaml
          observer_input_freshness:
            room_temperature:
              mode: event_driven
              stale_after: 15min
              availability: existing_room_sensor_healthy
```

That ID must already exist. Unknown or false health pauses learning. A latched
health flag is itself only as reliable as its source; it is not a heartbeat.
The generic example needs neither Home Assistant nor an API component. Enabling
`require_api_connection` requires an existing `api:` configuration. It checks
for a connected client with a state subscription, excluding log-only clients;
loss pauses learning within the one-second guard interval. This is a transport
check, **not proof of physical sensor health or authentication of that subscriber
as Home Assistant**. Another subscribed client can mask HA's absence. Reconnect
does not rewrite input timestamps; previously invalid inputs remain invalid until
a valid publication arrives. A still-valid held input may resume after transport
recovery without a new physical measurement.

## Diagnostics: twelve entities per observer

The original seven entity names, IDs and device assignments stay unchanged.
Five additional diagnostic entities are generated for each room:

- `<Room> Room Temperature Input Age`
- `<Room> Outdoor Temperature Input Age`
- `<Room> Valve Command Input Age`
- `<Room> Supply Temperature Input Age`
- `<Room> Input Freshness Status`

Ages are seconds since the last **incoming raw publication**, valid or invalid;
never-received inputs report NaN/unknown. They refresh every ten seconds even
when training is suspended. Reusing a held value, a health check, an API reconnect
or a filtered heartbeat does not refresh the receipt timestamp. A 64-bit clock
keeps long-held values from appearing recent after the 32-bit clock wraps.

The text status reports each input separately, e.g.
`room=held_unconfirmed; outdoor=held_unconfirmed; valve=recent_publication; supply=recent_publication`.
Other states are `missing`, `expired`, `invalid_or_unavailable`, and
`health_unavailable`; `api_disconnected` is prepended when that gate fails.
This diagnostic describes numeric-input readiness. Existing Model Status still
reports learning state, missing operating flags, window/DHW protection and other
model conditions. Incoming invalid numeric publications suspend immediately;
health/window/API changes are checked at least once per second.

New readings are captured immediately by raw callbacks and used by the next
scheduled observation. They do not trigger extra training steps. All twelve
Stijn entities use `adaptive_climate_stijn`; Nick uses `adaptive_climate_nick`.
There is no migration of the existing seven entities in this update because
their names and devices do not change.

## What Home Assistant and heartbeat filters can establish

ESPHome 2026.10.0's [Home Assistant numeric sensor implementation](https://github.com/esphome/esphome/blob/2026.10.0/esphome/components/homeassistant/sensor/homeassistant_sensor.cpp)
parses incoming states as numbers and publishes NaN for nonnumeric states such
as `unknown` and `unavailable`. The observer rejects that raw NaN, even if a
downstream filter hides it. Attribute imports only expose the imported attribute,
so parent-entity availability may require a separate health signal.

The existing ClimateDevice temperature heartbeat is a **filter**. ESPHome's
[sensor publication path](https://github.com/esphome/esphome/blob/2026.10.0/esphome/components/sensor/sensor.cpp)
calls raw callbacks before filters; the
[heartbeat filter](https://github.com/esphome/esphome/blob/2026.10.0/esphome/components/sensor/filter.cpp)
emits its cached value downstream. It cannot confirm a physical measurement and
is deliberately not used to renew ages. The tests check these pinned upstream
code contracts as well as exercising the wrapper's callbacks.

If your physical sensor/integration supports periodic real measurement reports,
enable those at the source and use strict mode with a deadline longer than the
verified report interval. From the supplied thermostat YAML alone, we cannot
establish whether the actual temperature devices support such reporting. Do not
add a template timer that republishes a cache and calls it a new measurement.

Even a fresh HA publication can be a cached state replay after reconnect; age
here is receipt age, not measurement age. HA's API connection cannot distinguish
a stable silent sensor from a disconnected one if HA retains its last value.
Held mode explicitly accepts that ambiguity. Missing HA availability events,
stale binary operating flags, and stale health flags cannot be inferred from a
retained numeric value. Window/DHW handling is unchanged, including the existing
limitations of latched imported binary states. Quantized held room readings also
produce zero-change training intervals; more samples do not prove accuracy.

No runtime state is persisted across firmware reboot. Verify both rooms' input
ages/status and observed temperatures after installation before trusting forecasts.
