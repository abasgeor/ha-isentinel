"""Sensor platform for iSentinel LP-gas tanks."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import IsentinelConfigEntry
from .const import CONF_AREA, CONF_TANKS, DOMAIN, MANUFACTURER
from .coordinator import IsentinelCoordinator


def _last(t: dict[str, Any]) -> dict[str, Any]:
    return t.get("last_event") or {}


def _num(v: Any) -> float | None:
    if v in (None, "", -1):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _refill_dt(t: dict[str, Any]) -> datetime | None:
    d = (t.get("last_fill_event") or {}).get("date")
    if not d:
        return None
    parsed = dt_util.parse_datetime(str(d).replace(" ", "T"))
    return dt_util.as_local(parsed) if parsed else None


@dataclass(frozen=True, kw_only=True)
class TankSensor(SensorEntityDescription):
    """Describes an iSentinel tank sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[TankSensor, ...] = (
    TankSensor(
        key="level",
        translation_key="level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gas-cylinder",
        value_fn=lambda t: _num(_last(t).get("tank_level")),
    ),
    TankSensor(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda t: _num(_last(t).get("battery")),
    ),
    TankSensor(
        key="signal",
        translation_key="signal",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:signal",
        value_fn=lambda t: _num(_last(t).get("signal_strength")),
    ),
    TankSensor(
        key="capacity",
        translation_key="capacity",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:propane-tank",
        value_fn=lambda t: _num(t.get("tank_capacity")),
    ),
    TankSensor(
        key="last_refill",
        translation_key="last_refill",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:gas-station",
        value_fn=_refill_dt,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IsentinelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create sensors for the tanks selected for this HA instance."""
    coordinator = entry.runtime_data
    selected = entry.data.get(CONF_TANKS) or list(coordinator.data.keys())
    entities: list[IsentinelSensor] = []
    for tid in selected:
        if tid in coordinator.data:
            for desc in SENSORS:
                entities.append(IsentinelSensor(coordinator, tid, desc))
    async_add_entities(entities)


class IsentinelSensor(CoordinatorEntity[IsentinelCoordinator], SensorEntity):
    """A single reading of an iSentinel tank."""

    _attr_has_entity_name = True
    entity_description: TankSensor

    def __init__(
        self, coordinator: IsentinelCoordinator, tank_id: str, description: TankSensor
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._tank_id = tank_id
        self._attr_unique_id = f"{tank_id}_{description.key}"
        tank = coordinator.data[tank_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, tank_id)},
            name=tank.get("alias") or f"iSentinel {tank_id}",
            manufacturer=MANUFACTURER,
            model="LP gas tank monitor",
            suggested_area=coordinator.config_entry.data.get(CONF_AREA),
        )

    @property
    def _tank(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._tank_id) or {}

    @property
    def available(self) -> bool:
        return super().available and self._tank_id in self.coordinator.data

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._tank)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key != "level":
            return None
        t = self._tank
        fill = t.get("last_fill_event") or {}
        return {
            "alert_threshold": t.get("level_alert"),
            "capacity_liters": _num(t.get("tank_capacity")),
            "last_measurement": _last(t).get("date"),
            "last_refill_date": fill.get("date"),
            "last_refill_added_pct": fill.get("difference_tank_level"),
            "last_refill_to_pct": fill.get("final_tank_level"),
            "isentinel_id": self._tank_id,
        }
