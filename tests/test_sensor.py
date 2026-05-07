"""Tests for the five sensor entities."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfPower

from custom_components.solarmatrix.api import Snapshot
from custom_components.solarmatrix.sensor import (
    BatteryPower,
    BatterySOC,
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
    return Snapshot(0, 100, 374, 21, 42, -41, 45)


def test_solar_power_attrs() -> None:
    s = SolarPower(_coord(_snap()), system_name="Sys", household_name="WE05")
    assert s.device_class == SensorDeviceClass.POWER
    assert s.state_class == SensorStateClass.MEASUREMENT
    assert s.native_unit_of_measurement == UnitOfPower.WATT
    assert s.native_value == 42


def test_mi_out_power_attrs() -> None:
    s = MIOutPower(_coord(_snap()), system_name="Sys", household_name="WE05")
    assert s.native_value == 21


def test_grid_power_attrs() -> None:
    s = GridPower(_coord(_snap()), system_name="Sys", household_name="WE05")
    assert s.native_value == 374


def test_battery_power_signed() -> None:
    s = BatteryPower(_coord(_snap()), system_name="Sys", household_name="WE05")
    assert s.native_value == -41
    assert s.device_class == SensorDeviceClass.POWER


def test_battery_soc_attrs() -> None:
    s = BatterySOC(_coord(_snap()), system_name="Sys", household_name="WE05")
    assert s.device_class == SensorDeviceClass.BATTERY
    assert s.state_class == SensorStateClass.MEASUREMENT
    assert s.native_unit_of_measurement == PERCENTAGE
    assert s.native_value == 45


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
