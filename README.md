# SolarMatrix Home Assistant Integration

Polls a SolarMatrix system per household and exposes its live energy data
to Home Assistant. Designed for the Energy Dashboard.

## Install

1. Add this repo as a HACS custom repository.
2. Install **SolarMatrix** from HACS.
3. Restart Home Assistant.
4. Settings → Devices & Services → Add Integration → SolarMatrix.
5. Paste your API key (create one at app.solarmatrix.app under your
   account → API keys), then pick a household.

## Sensors

| Entity | Unit |
|---|---|
| Solar power | W |
| Microinverter output | W |
| Consumption | W |
| Battery power (signed: + charging, − discharging) | W |
| Battery state of charge | % |

## Energy Dashboard

The Energy Dashboard expects cumulative kWh sensors. Use the built-in
Riemann helper to integrate the watt sensors above into kWh:

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
`battery_out` ≤ 0 so the Energy Dashboard can attribute charge vs.
discharge). Then in **Settings → Dashboards → Energy**, point each card at
the matching Riemann sensor.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

## Translations

The integration ships translations for the full HA-supported locale list
(see `scripts/locales.json`). The non-English files in
`custom_components/solarmatrix/translations/` are currently machine-translated
placeholders — running maintainers should regenerate them with a real LLM
backend before each release:

```bash
OPENAI_API_KEY=sk-... python scripts/translate.py
# or:
ANTHROPIC_API_KEY=sk-ant-... MODEL=anthropic python scripts/translate.py
```

The drift check (run in CI as `python scripts/translate.py --check`) only
reads files; it does not call any LLM and so does not need credentials.
