"""Coordinator and entities for an EA flood alert or warning area."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .floods import (
    STATES,
    FloodArea,
    FloodError,
    FloodWarning,
    get_flood_warning,
    severity_state,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "eafm_enhanced"
CONF_FLOOD_AREA = "flood_area"
# The EA updates alerts and warnings every 15 minutes.
FLOOD_UPDATE_INTERVAL = timedelta(minutes=5)
ATTRIBUTION = (
    "This uses Environment Agency flood and river level data from the "
    "real-time data API (Beta)"
)


class FloodAreaCoordinator(DataUpdateCoordinator[FloodWarning | None]):
    """Polls the EA for the current alert or warning in one area."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: Any,
        area: FloodArea,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {area.notation}",
            update_interval=FLOOD_UPDATE_INTERVAL,
        )
        self._session = session
        self.area = area

    async def _async_update_data(self) -> FloodWarning | None:
        try:
            return await get_flood_warning(self._session, self.area.notation)
        except FloodError as err:
            raise UpdateFailed(str(err)) from err


class FloodAreaEntity(CoordinatorEntity[FloodAreaCoordinator]):
    """Base entity: one device per flood area."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: FloodAreaCoordinator, key: str) -> None:
        super().__init__(coordinator)
        area = coordinator.area
        self._attr_translation_key = key
        self._attr_unique_id = f"flood_area_{area.notation}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"flood_area_{area.notation}")},
            name=area.label,
            manufacturer="Environment Agency",
            model=area.kind.capitalize(),
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=area.url,
        )

    @property
    def _in_force(self) -> bool:
        warning = self.coordinator.data
        return warning is not None and warning.in_force


class FloodWarningSensor(FloodAreaEntity, SensorEntity):
    """The alert or warning in force: none, alert, warning or severe."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATES

    @property
    def native_value(self) -> str:
        warning = self.coordinator.data
        return severity_state(warning.severity_level if warning else None)

    @property
    def icon(self) -> str:
        return "mdi:home-flood" if self._in_force else "mdi:water-check"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        area = self.coordinator.area
        warning = self.coordinator.data if self._in_force else None
        return {
            "area": area.label,
            "area_code": area.notation,
            "area_type": area.kind,
            "description": area.description,
            "county": area.county,
            "river_or_sea": area.river_or_sea,
            "url": area.url,
            "severity": warning.severity if warning else None,
            "message": warning.message if warning else None,
            "time_raised": _iso(warning.time_raised) if warning else None,
            "time_severity_changed": (
                _iso(warning.time_severity_changed) if warning else None
            ),
            "time_message_changed": (
                _iso(warning.time_message_changed) if warning else None
            ),
        }


class FloodWarningInForce(FloodAreaEntity, BinarySensorEntity):
    """On while any alert or warning is in force for the area."""

    _attr_device_class = BinarySensorDeviceClass.SAFETY

    @property
    def is_on(self) -> bool:
        return self._in_force


def _iso(value) -> str | None:
    return value.isoformat() if value else None
