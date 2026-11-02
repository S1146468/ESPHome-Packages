# Continuous collection without firmware deployment

The collector now defaults to Home Assistant's authenticated WebSocket
`state_changed` subscription. One connection receives changes instead of polling
all states every ten seconds. It subscribes before retrieving an initial state
snapshot, preserves both event order and HA timestamps, filters stored events
to `collection_entities.json`, and never calls services or writes HA states.
The subscription receives HA state changes globally and filters locally; it
does not subscribe to every event type. This is better evidence for intermediate
state/attribute transitions than snapshots, but not a guarantee of physical
sensor acquisition or identical-value reports. `state_reported` is not assumed
to be publicly subscribable in the same way. A future observer cycle payload
with a changing sequence can be captured as an ordinary state change.

## Recorded evidence

JSONL records contain a unique collector `run_id`, per-run sequence, collector
UTC receipt time and monotonic receipt time. HA events retain `time_fired`,
entity timestamps, old/new states and attributes without rewriting them.
Unknown/unavailable values and entity removals (`new_state: null`) remain
explicit. A startup/reconnect snapshot is marked `boundary_snapshot`, never
promoted to a new measurement. Events can arrive before the snapshot response;
retain their recorded order and do not apply the boundary snapshot as a later
measurement update. No cache deduplication deletes actual received events.

Connections retry with bounded exponential delay from 1 to 60 seconds.
`collection_gap` records retain only an exception type, not possibly sensitive
exception text. Silent connections use a ping/pong heartbeat after 30 seconds;
missing replies reconnect. Heartbeats prove transport liveness only. Events lost
during disconnection are not backfilled; resumed snapshots do not erase gaps.
Clean SIGINT/SIGTERM stop writes a stop record; stopping may take up to the
30-second socket timeout. A killed process or power loss leaves an unclosed run;
the next run is independent, and an incomplete final line is preserved then
isolated with a newline/recovery marker. Readers must flag that malformed line,
not silently treat it as an event. Never merge collector runs into continuous
coverage without assessing the intervening gap.

Files append across restarts; the OS-held lock prevents concurrent writers to
the same output and releases automatically after crashes. Each record flushes;
fsync occurs every ten seconds and on clean close. Abrupt power loss can lose
the unsynced tail. At 128 MiB the current file is renamed with a unique UTC
suffix and a new active file is opened, retaining run/sequence continuity.
All segments must be retained. There is no automatic deletion/retention policy;
monitor free disk space and archive older segments externally. Disk exhaustion
is an error, not permission to discard old measurements.

## Installation on a machine that can reach HA

No address/credentials were provided and no live HA connection was attempted.
Run the explicit one-shot check below on the intended collection host first.
Python 3.11+ is sufficient. From the repository directory on Linux:

```sh
python3 -m venv .venv-collector
.venv-collector/bin/python -m pip install -r AdaptiveClimate/evaluation/requirements-collection.txt
install -d -m 700 "$HOME/.config/adaptive-climate" "$HOME/adaptive-climate-data"
```

Create a Home Assistant long-lived token for a dedicated non-administrator user
with access to the selected entities. HA tokens are not assumed to enforce a
read-only API scope; the collector's command set is read-only. Save the token
alone in `$HOME/.config/adaptive-climate/token` using an editor, then:

```sh
chmod 600 "$HOME/.config/adaptive-climate/token"
export HA_URL='https://YOUR-HOME-ASSISTANT-HOST'
export HA_TOKEN_FILE="$HOME/.config/adaptive-climate/token"
.venv-collector/bin/python AdaptiveClimate/evaluation/collect_states.py AdaptiveClimate/evaluation/collection_entities.json "$HOME/adaptive-climate-data/reachability.jsonl" --once
```

Replace the URL before running. Exit 0 means the REST request succeeded; inspect
`missing_entities` and returned availability before expecting useful capture.
Exit 1 records a failure. A successful snapshot is not proof WebSocket proxy
upgrades work. Start event mode in the foreground, verify a `connected` record,
`boundary_snapshot`, then actual `state_changed` events:

```sh
.venv-collector/bin/python AdaptiveClimate/evaluation/collect_states.py AdaptiveClimate/evaluation/collection_entities.json "$HOME/adaptive-climate-data/observations.jsonl"
```

HTTPS certificate verification remains enabled. Trusted local HTTP is supported
only with explicit `--allow-http`; it sends credentials without transport
encryption, so prefer HTTPS or an authenticated encrypted network path. Do not
put tokens in URLs, command-line arguments, Git, screenshots or output logs.
`HA_TOKEN` is an optional environment fallback; a protected token file is
preferred. No secrets are written by the collector.

For a Linux systemd user service, save this as
`~/.config/systemd/user/adaptive-climate-collector.service`, replacing every
absolute path and URL with the real values (systemd does not expand shell
variables in ExecStart):

```ini
[Unit]
Description=Adaptive Climate read-only history collector
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/ABSOLUTE/PATH/ESPHome-Packages
Environment=HA_URL=https://YOUR-HOME-ASSISTANT-HOST
Environment=HA_TOKEN_FILE=/ABSOLUTE/PATH/token
ExecStart=/ABSOLUTE/PATH/ESPHome-Packages/.venv-collector/bin/python AdaptiveClimate/evaluation/collect_states.py AdaptiveClimate/evaluation/collection_entities.json /ABSOLUTE/PATH/observations.jsonl
Restart=on-failure
RestartSec=30
TimeoutStopSec=40
UMask=0077
NoNewPrivileges=true

[Install]
WantedBy=default.target
```

```sh
systemctl --user daemon-reload
systemctl --user enable --now adaptive-climate-collector.service
systemctl --user status adaptive-climate-collector.service
```

User services normally follow the login session; use an always-on logged-in
host or have its administrator configure user lingering where appropriate.
Do not enable a service until the foreground connectivity test works.

On Windows, use `py -m venv .venv-collector`, then
`.venv-collector\Scripts\python.exe -m pip install -r AdaptiveClimate/evaluation/requirements-collection.txt`.
Set `$env:HA_URL` and `$env:HA_TOKEN_FILE` in PowerShell, use that Python executable
with the same arguments, and secure the token/data directory using the current
user's Windows file permissions. For Task Scheduler, use a small local launch
script that sets those environment variables (token path only), starts Python
with absolute paths, and configure restart-on-failure and no overlapping task
instances. The machine must remain awake and connected.

## Explicit fallback

`--mode poll --interval 60` uses REST snapshots once per minute, with failure
backoff. Minimum permitted interval is ten seconds. This preserves timestamps
but misses intermediate changes and is a lower evidence level, not an event
subscription substitute. `--once` always performs one REST check regardless of
mode. Neither mode reconstructs historical physical samples or exact firmware
issue timestamps.

Protocol references: [HA WebSocket API](https://developers.home-assistant.io/docs/api/websocket/)
and [HA REST API](https://developers.home-assistant.io/docs/api/rest/).
Automated tests use mocked HTTP/WebSocket messages and temporary journals;
they do not establish real network reachability or host long-term reliability.
