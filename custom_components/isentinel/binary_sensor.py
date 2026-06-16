"""Binary sensors for iSentinel tanks (low gas / low battery alerts)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import IsentinelConfigEntry
from .const import CONF_AREA, CONF_TANKS, DOMAIN, MANUFACTURER
from .coordinator import IsentinelCoordinator

BATTERY_LOW_PCT = 20


def _last(t: dict[str, Any]) -> dict[str, Any]:
    return t.get("last_event") or {}


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_low(t: dict[str, Any]) -> bool | None:
    level = _num(_last(t).get("tank_level"))
    alert = _num(t.get("level_alert"))
    if level is None:
        return None
    if alert is None:
        return False
    return level <= alert


def _battery_low(t: dict[str, Any]) -> bool | None:
    b = _num(_last(t).get("battery"))
    return None if b is None else b <= BATTERY_LOW_PCT


@dataclass(frozen=True, kw_only=True)
class TankBinary(BinarySensorEntityDescription):
    """Describes an iSentinel tank binary sensor."""

    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSORS: tuple[TankBinary, ...] = (
    TankBinary(
        key="low",
        translation_key="low",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_is_low,
    ),
    TankBinary(
        key="battery_low",
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_battery_low,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IsentinelConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create binary sensors for the tanks selected for this HA instance."""
    coordinator = entry.runtime_data
    selected = entry.data.get(CONF_TANKS) or list(coordinator.data.keys())
    entities: list[IsentinelBinarySensor] = []
    for tid in selected:
        if tid in coordinator.data:
            for desc in BINARY_SENSORS:
                entities.append(IsentinelBinarySensor(coordinator, tid, desc))
    async_add_entities(entities)


class IsentinelBinarySensor(CoordinatorEntity[IsentinelCoordinator], BinarySensorEntity):
    """A tank alert (low gas / low battery)."""

    _attr_has_entity_name = True
    entity_description: TankBinary

    def __init__(
        self, coordinator: IsentinelCoordinator, tank_id: str, description: TankBinary
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
        return (
            super().available
            and self._tank_id in self.coordinator.data
            and self.entity_description.value_fn(self._tank) is not None
        )

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self._tank)
