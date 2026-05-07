"""Tests for the five sensor entities."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfPower

from custom_components.solarmatrix.api import EnergyTotals, Snapshot
from custom_components.solarmatrix.sensor import (
    BatteryPower,
    BatterySOC,
    ConsumptionPower,
    GridPower,
    MIOutPower,
    SolarPower,
)


def _coord(snapshot: Snapshot, success: bool = True) -> MagicMock:
    coord = MagicMock()
    coord.data = snapshot
    coord.last_update_success = success
    coord.config_entry_id = "entry-id"
    coord.sid = "sid-1"
    coord.hid = 0
    return coord


def _snap() -> Snapshot:
    return _snap_with_energy()


def _snap_with_energy() -> Snapshot:
    return Snapshot(
        household_id=0,
        ts_ms=100,
        grid_w=58,
        mi_out_w=200,
        solar_w=484,
        battery_w=954,
        battery_soc_pct=23,
        energy=EnergyTotals(
            solar_generation_mws=12_345_678_901_234,
            microinverter_output_mws=9_876_543_210_987,
            grid_import_mws=2_345_678_901_234,
            grid_export_mws=123_456_789_012,
            battery_charge_mws=5_678_901_234_567,
            battery_discharge_mws=5_345_678_901_234,
        ),
    )


def test_solar_power_attrs() -> None:
    snap = _snap_with_energy()
    s = SolarPower(_coord(snap), system_name="Sys", household_name="WE05")
    assert s.device_class == SensorDeviceClass.POWER
    assert s.state_class == SensorStateClass.MEASUREMENT
    assert s.native_unit_of_measurement == UnitOfPower.WATT
    assert s.native_value == snap.solar_w


def test_mi_out_power_attrs() -> None:
    snap = _snap_with_energy()
    s = MIOutPower(_coord(snap), system_name="Sys", household_name="WE05")
    assert s.native_value == snap.mi_out_w


def test_grid_power_attrs() -> None:
    snap = _snap_with_energy()
    s = GridPower(_coord(snap), system_name="Sys", household_name="WE05")
    assert s.native_value == snap.grid_w


def test_battery_power_signed() -> None:
    snap = _snap_with_energy()
    s = BatteryPower(_coord(snap), system_name="Sys", household_name="WE05")
    assert s.native_value == snap.battery_w
    assert s.device_class == SensorDeviceClass.POWER


def test_battery_soc_attrs() -> None:
    snap = _snap_with_energy()
    s = BatterySOC(_coord(snap), system_name="Sys", household_name="WE05")
    assert s.device_class == SensorDeviceClass.BATTERY
    assert s.state_class == SensorStateClass.MEASUREMENT
    assert s.native_unit_of_measurement == PERCENTAGE
    assert s.native_value == snap.battery_soc_pct


def test_unique_ids_are_distinct() -> None:
    coord = _coord(_snap())
    sensors = [
        SolarPower(coord, "Sys", "WE05"),
        MIOutPower(coord, "Sys", "WE05"),
        GridPower(coord, "Sys", "WE05"),
        BatteryPower(coord, "Sys", "WE05"),
        BatterySOC(coord, "Sys", "WE05"),
    ]
    ids = {s.unique_id for s in sensors}
    assert len(ids) == 5


def test_available_reflects_coordinator() -> None:
    coord_ok = _coord(_snap(), success=True)
    coord_fail = _coord(_snap(), success=False)
    assert SolarPower(coord_ok, "Sys", "WE05").available is True
    assert SolarPower(coord_fail, "Sys", "WE05").available is False


def test_consumption_power_attrs() -> None:
    snap = _snap_with_energy()
    coord = _coord(snap)
    s = ConsumptionPower(coord, system_name="Sys", household_name="WE05")
    assert s.device_class == SensorDeviceClass.POWER
    assert s.state_class == SensorStateClass.MEASUREMENT
    assert s.native_unit_of_measurement == UnitOfPower.WATT
    # mi_out_w + grid_w
    assert s.native_value == snap.mi_out_w + snap.grid_w
