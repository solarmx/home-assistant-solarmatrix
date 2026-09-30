# SolarMatrix Home Assistant Integration

Live energy data from a SolarMatrix system in Home Assistant, ready for
the Energy Dashboard.

Each household exposes twelve sensors:

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

---

## Install

### 1. Get an API key

Open <https://portal.solarmatrix.eu/settings/api-keys> and create a key.

### 2. Add this repository to HACS

In Home Assistant: **HACS → ⋮ (top-right) → Custom repositories → Add**.

- Repository: `https://github.com/solarmx/home-assistant-solarmatrix`
- Category: **Integration**

### 3. Install SolarMatrix from HACS

Find **SolarMatrix** in the HACS list and click **Download**. Restart
Home Assistant when prompted.

![HACS dashboard with SolarMatrix downloaded](docs/screenshots/09-hacs-dashboard.png)

### 4. Add the integration

**Settings → Devices & Services → Add Integration → SolarMatrix.**

Paste the API key from step 1 and submit.

![Connect to SolarMatrix dialog](docs/screenshots/01-config-flow-user.png)

A device appears under SolarMatrix with twelve sensors.

![Device page with all twelve sensors](docs/screenshots/05-device-entities.png)

---

## Energy Dashboard

**Settings → Dashboards → Energy → Electricity tab.**

### Electricity grid

**Add grid connection.** Pick:

- *Energy imported from grid* → **Grid import energy**
- *Energy exported to grid* → **Grid export energy**

![Configure grid connection dialog](docs/screenshots/07-energy-grid-edit.png)

### Solar panels

**Add solar production** → pick **Solar production energy**.

### Home battery storage

**Add battery system**:

- *Energy going in to the battery* → **Battery charge energy**
- *Energy coming out of the battery* → **Battery discharge energy**

### Final state

![Energy dashboard configuration](docs/screenshots/06-energy-config.png)

Open the **Energy** dashboard from the sidebar.

![Energy dashboard with live data](docs/screenshots/08-energy-dashboard.png)
