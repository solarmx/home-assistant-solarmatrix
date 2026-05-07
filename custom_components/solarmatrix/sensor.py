"""Sensor entities for SolarMatrix."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Snapshot
from .const import (
    CONF_HOUSEHOLD_NAME,
    CONF_SYSTEM_NAME,
    DOMAIN,
)
from .coordinator import SolarMatrixCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add SolarMatrix sensors for one config entry."""
    coordinator: SolarMatrixCoordinator = hass.data[DOMAIN][entry.entry_id]
    system_name: str = entry.data[CONF_SYSTEM_NAME]
    household_name: str = entry.data[CONF_HOUSEHOLD_NAME]

    async_add_entities(
        [
            SolarPower(coordinator, system_name, household_name),
            MIOutPower(coordinator, system_name, household_name),
            GridPower(coordinator, system_name, household_name),
            BatteryPower(coordinator, system_name, household_name),
            BatterySOC(coordinator, system_name, household_name),
            ConsumptionPower(coordinator, system_name, household_name),
            SolarEnergy(coordinator, system_name, household_name),
            MIOutEnergy(coordinator, system_name, household_name),
            GridImportEnergy(coordinator, system_name, household_name),
            GridExportEnergy(coordinator, system_name, household_name),
            BatteryChargeEnergy(coordinator, system_name, household_name),
            BatteryDischargeEnergy(coordinator, system_name, household_name),
        ]
    )


class _BaseSensor(CoordinatorEntity[SolarMatrixCoordinator], SensorEntity):
    """Base for all SolarMatrix sensors."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: SolarMatrixCoordinator,
        system_name: str,
        household_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._system_name = system_name
        self._household_name = household_name
        self._attr_unique_id = f"{coordinator.sid}:{coordinator.hid}:{self._slug()}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.sid}:{coordinator.hid}")},
            name=f"{system_name} — {household_name}",
            manufacturer="SolarMatrix",
        )

    def _slug(self) -> str:
        raise NotImplementedError

    @property
    def available(self) -> bool:  # type: ignore[override]
        return self.coordinator.last_update_success and self.coordinator.data is not None

    def _snap(self) -> Snapshot:
        return self.coordinator.data


class _PowerSensor(_BaseSensor):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT


class _EnergySensor(_BaseSensor):
    """Lifetime cumulative kWh, server-side counter."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 3

    _MWS_PER_KWH = 3_600_000_000

    def _mws(self) -> int:
        raise NotImplementedError

    @property
    def native_value(self) -> float:
        return round(self._mws() / self._MWS_PER_KWH, 3)


class SolarPower(_PowerSensor):
    _attr_translation_key = "solar_power"

    def _slug(self) -> str:
        return "solar_power"

    @property
    def native_value(self) -> int:
        return self._snap().solar_w


class MIOutPower(_PowerSensor):
    _attr_translation_key = "mi_out_power"

    def _slug(self) -> str:
        return "mi_out_power"

    @property
    def native_value(self) -> int:
        return self._snap().mi_out_w


class GridPower(_PowerSensor):
    _attr_translation_key = "grid_power"

    def _slug(self) -> str:
        return "grid_power"

    @property
    def native_value(self) -> int:
        return self._snap().grid_w


class BatteryPower(_PowerSensor):
    _attr_translation_key = "battery_power"

    def _slug(self) -> str:
        return "battery_power"

    @property
    def native_value(self) -> int:
        return self._snap().battery_w


class BatterySOC(_BaseSensor):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_translation_key = "battery_soc"

    def _slug(self) -> str:
        return "battery_soc"

    @property
    def native_value(self) -> int:
        return self._snap().battery_soc_pct


class ConsumptionPower(_PowerSensor):
    """Live home consumption: microinverter output + grid (signed)."""

    _attr_translation_key = "consumption_power"

    def _slug(self) -> str:
        return "consumption_power"

    @property
    def native_value(self) -> int:
        s = self._snap()
        return s.mi_out_w + s.grid_w


class SolarEnergy(_EnergySensor):
    _attr_translation_key = "solar_energy"

    def _slug(self) -> str:
        return "solar_energy"

    def _mws(self) -> int:
        return self._snap().energy.solar_generation_mws


class MIOutEnergy(_EnergySensor):
    _attr_translation_key = "mi_out_energy"

    def _slug(self) -> str:
        return "mi_out_energy"

    def _mws(self) -> int:
        return self._snap().energy.microinverter_output_mws


class GridImportEnergy(_EnergySensor):
    _attr_translation_key = "grid_import_energy"

    def _slug(self) -> str:
        return "grid_import_energy"

    def _mws(self) -> int:
        return self._snap().energy.grid_import_mws


class GridExportEnergy(_EnergySensor):
    _attr_translation_key = "grid_export_energy"

    def _slug(self) -> str:
        return "grid_export_energy"

    def _mws(self) -> int:
        return self._snap().energy.grid_export_mws


class BatteryChargeEnergy(_EnergySensor):
    _attr_translation_key = "battery_charge_energy"

    def _slug(self) -> str:
        return "battery_charge_energy"

    def _mws(self) -> int:
        return self._snap().energy.battery_charge_mws


class BatteryDischargeEnergy(_EnergySensor):
    _attr_translation_key = "battery_discharge_energy"

    def _slug(self) -> str:
        return "battery_discharge_energy"

    def _mws(self) -> int:
        return self._snap().energy.battery_discharge_mws
