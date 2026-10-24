"""Environment Agency flood alerts and warnings for one area.

The EA issues flood alerts for wide "alert areas" and flood warnings (and
severe flood warnings) for smaller "warning areas". Each area has a code:
warning areas have "FW" after the three-digit region, alert areas "WA".
See https://environment.data.gov.uk/flood-monitoring/doc/reference
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp

API = "https://environment.data.gov.uk/flood-monitoring/id"
AREAS_URL = f"{API}/floodAreas"
FLOODS_URL = f"{API}/floods"
AREA_PAGE_URL = "https://check-for-flooding.service.gov.uk/target-area/{notation}"

_TIMEOUT = aiohttp.ClientTimeout(total=30)

# EA severity levels: 1 severe flood warning, 2 flood warning, 3 flood alert,
# 4 warning no longer in force (shown for a day after it is removed).
SEVERITY_STATES = {1: "severe_flood_warning", 2: "flood_warning", 3: "flood_alert"}
STATES = ["none", "flood_alert", "flood_warning", "severe_flood_warning"]


class FloodError(Exception):
    """Raised when the EA API can't be reached or returns bad data."""


def severity_state(level: int | None) -> str:
    """The sensor state for an EA severity level."""
    return SEVERITY_STATES.get(level, "none")


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class FloodArea:
    """An EA flood alert or flood warning area."""

    notation: str
    label: str
    description: str | None
    county: str | None
    river_or_sea: str | None

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> FloodArea:
        return cls(
            notation=item["notation"],
            label=item.get("label") or item.get("description") or item["notation"],
            description=item.get("description"),
            county=item.get("county"),
            river_or_sea=item.get("riverOrSea"),
        )

    @property
    def kind(self) -> str:
        return (
            "flood warning area" if self.notation[3:5] == "FW" else "flood alert area"
        )

    @property
    def url(self) -> str:
        return AREA_PAGE_URL.format(notation=self.notation)


@dataclass(frozen=True, slots=True)
class FloodWarning:
    """An alert or warning the EA has issued for an area."""

    area: str
    severity_level: int | None
    severity: str | None
    message: str | None
    time_raised: datetime | None
    time_severity_changed: datetime | None
    time_message_changed: datetime | None

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> FloodWarning:
        level = item.get("severityLevel")
        return cls(
            area=item.get("floodAreaID") or "",
            severity_level=level if isinstance(level, int) else None,
            severity=item.get("severity"),
            message=(item.get("message") or "").strip() or None,
            time_raised=_time(item.get("timeRaised")),
            time_severity_changed=_time(item.get("timeSeverityChanged")),
            time_message_changed=_time(item.get("timeMessageChanged")),
        )

    @property
    def in_force(self) -> bool:
        return self.severity_level in SEVERITY_STATES


async def _get(
    session: aiohttp.ClientSession,
    url: str,
    params: dict[str, str] | None = None,
    missing_ok: bool = False,
) -> dict[str, Any] | None:
    try:
        async with session.get(url, params=params, timeout=_TIMEOUT) as response:
            if missing_ok and response.status == 404:
                return None
            response.raise_for_status()
            body = await response.json()
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise FloodError(f"EA flood API request failed: {err}") from err
    if not isinstance(body, dict):
        raise FloodError("EA flood API returned an unexpected response")
    return body


async def get_flood_areas(
    session: aiohttp.ClientSession, latitude: float, longitude: float, radius_km: float
) -> list[FloodArea]:
    """Flood alert and warning areas within a distance of a point."""
    body = await _get(
        session,
        AREAS_URL,
        {"lat": f"{latitude:g}", "long": f"{longitude:g}", "dist": f"{radius_km:g}"},
    )
    return [
        FloodArea.from_api(item)
        for item in body.get("items") or []
        if isinstance(item, dict) and item.get("notation")
    ]


async def get_flood_area(session: aiohttp.ClientSession, notation: str) -> FloodArea:
    """One flood area's details."""
    item = (await _get(session, f"{AREAS_URL}/{notation}")).get("items")
    if not isinstance(item, dict) or not item.get("notation"):
        raise FloodError(f"EA flood area {notation} not found")
    return FloodArea.from_api(item)


async def get_flood_warning(
    session: aiohttp.ClientSession, notation: str
) -> FloodWarning | None:
    """The alert or warning for an area, or None if there isn't one.

    The EA answers 404 when nothing has been issued for the area.
    """
    body = await _get(session, f"{FLOODS_URL}/{notation}", missing_ok=True)
    if body is None:
        return None
    item = body.get("items")
    if isinstance(item, list):
        item = item[0] if item else None
    if not isinstance(item, dict):
        raise FloodError(f"EA flood API returned no warning data for {notation}")
    return FloodWarning.from_api(item)
