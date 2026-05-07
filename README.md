# SolarMatrix Home Assistant Integration

Live energy data from a SolarMatrix system, surfaced as Home Assistant
sensors and ready for the Energy Dashboard.

The integration polls the cloud API every 5 seconds over a single
keep-alive connection and exposes twelve sensors per configured household:

| Entity | Unit |
|---|---|
| Solar power | W |
| Microinverter output | W |
| Grid power (signed: + import, − export) | W |
| Battery power (signed: + charging, − discharging) | W |
| Battery state of charge | % |
| Consumption (microinverter + grid) | W |
| Solar production energy | kWh |
| Microinverter output energy | kWh |
| Grid import energy | kWh |
| Grid export energy | kWh |
| Battery charge energy | kWh |
| Battery discharge energy | kWh |

## Install

1. In HACS, add this repo as a custom repository (category: *Integration*):
   `https://github.com/solarmx/home-assistant-solarmatrix`
2. Install **SolarMatrix** from HACS.
3. Restart Home Assistant.
4. Settings → Devices & Services → **Add Integration** → SolarMatrix.
5. Paste an API key, then pick the household you want to monitor.
   Create or manage keys at <https://app.solarmatrix.eu/settings/api-keys>.

To monitor a second household, add the integration again. Use a different
API key, or otherwise lower the polling cadence on one of the entries to
stay below the per-key rate limit.

## Energy Dashboard

The integration exposes lifetime kWh counters directly. Configure under
**Settings → Dashboards → Energy**:

- Solar production: `sensor.<…>_solar_production_energy`
- Grid consumption: `sensor.<…>_grid_import_energy`
- Return to grid: `sensor.<…>_grid_export_energy`
- Battery in: `sensor.<…>_battery_charge_energy`
- Battery out: `sensor.<…>_battery_discharge_energy`

Home Assistant derives the "Home consumption" tile automatically from
those.

No Riemann helpers needed. Numbers match the SolarMatrix portal exactly.
