# SolarMatrix Home Assistant Integration

Live energy data from a SolarMatrix system, surfaced as Home Assistant
sensors and ready for the Energy Dashboard.

The integration polls the cloud API every 5 seconds over a single
keep-alive connection and exposes five sensors per configured household:

| Entity | Unit |
|---|---|
| Solar power | W |
| Microinverter output | W |
| Consumption | W |
| Battery power (signed: + charging, − discharging) | W |
| Battery state of charge | % |

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

The Energy Dashboard expects cumulative kWh sensors. Convert the live
watt sensors above with Home Assistant's built-in Riemann helper:

```yaml
sensor:
  - platform: integration
    source: sensor.solarmatrix_solar_power
    name: Solar Production Energy
    unit_prefix: k
    method: left
```

Repeat for `consumption`, `microinverter_output`, and the two halves of
`battery_power` (split with a template into `battery_in` ≥ 0 and
`battery_out` ≤ 0 so the dashboard can show charge vs. discharge).
Then in **Settings → Dashboards → Energy**, point each card at the
matching Riemann sensor.
