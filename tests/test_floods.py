"""Tests for the EA flood warnings client."""

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.eafm_enhanced.floods import (
    AREAS_URL,
    FLOODS_URL,
    FloodArea,
    FloodError,
    FloodWarning,
    get_flood_area,
    get_flood_areas,
    get_flood_warning,
    severity_state,
)
from tests.conftest import ALERT_AREA, WARNING_AREA, load_fixture


def test_area_kind_comes_from_its_code() -> None:
    alert = FloodArea.from_api(load_fixture("flood_area_031WAF120.json")["items"])
    warning = FloodArea.from_api(load_fixture("flood_area_warning.json")["items"])

    assert alert.notation == ALERT_AREA
    assert alert.label == "River Wye in Gloucestershire"
    assert alert.kind == "flood alert area"
    assert alert.river_or_sea == "River Wye"
    assert warning.kind == "flood warning area"
    assert warning.url == (
        f"https://check-for-flooding.service.gov.uk/target-area/{WARNING_AREA}"
    )


def test_warning_from_the_api() -> None:
    (item,) = load_fixture("floods_warning.json")["items"]

    warning = FloodWarning.from_api(item)

    assert warning.area == WARNING_AREA
    assert warning.severity_level == 2
    assert warning.severity == "Flood warning"
    assert warning.in_force
    assert warning.message
    assert warning.time_raised is not None


@pytest.mark.parametrize(
    ("level", "state"),
    [
        (None, "none"),
        (1, "severe_flood_warning"),
        (2, "flood_warning"),
        (3, "flood_alert"),
        (4, "none"),
    ],
)
def test_severity_state(level, state) -> None:
    assert severity_state(level) == state


def test_a_warning_no_longer_in_force() -> None:
    (item,) = load_fixture("floods_warning.json")["items"]
    item.update(severityLevel=4, severity="Warning no longer in force")

    assert not FloodWarning.from_api(item).in_force


async def test_get_flood_warning(hass, aioclient_mock) -> None:
    aioclient_mock.get(
        FLOODS_URL,
        params={"floodArea": WARNING_AREA},
        json=load_fixture("floods_warning.json"),
    )

    warning = await get_flood_warning(async_get_clientsession(hass), WARNING_AREA)

    assert warning.severity_level == 2


async def test_no_warning(hass, aioclient_mock) -> None:
    aioclient_mock.get(FLOODS_URL, params={"floodArea": ALERT_AREA}, json={"items": []})

    assert await get_flood_warning(async_get_clientsession(hass), ALERT_AREA) is None


async def test_most_severe_warning_wins(hass, aioclient_mock) -> None:
    (item,) = load_fixture("floods_warning.json")["items"]
    ended = {**item, "severityLevel": 4, "severity": "Warning no longer in force"}
    severe = {**item, "severityLevel": 1, "severity": "Severe flood warning"}
    aioclient_mock.get(
        FLOODS_URL,
        params={"floodArea": WARNING_AREA},
        json={"items": [ended, severe, item]},
    )

    warning = await get_flood_warning(async_get_clientsession(hass), WARNING_AREA)

    assert warning.severity_level == 1


@pytest.mark.parametrize("status", [500, 503])
async def test_errors_raise(hass, aioclient_mock, status) -> None:
    aioclient_mock.get(FLOODS_URL, params={"floodArea": ALERT_AREA}, status=status)

    with pytest.raises(FloodError):
        await get_flood_warning(async_get_clientsession(hass), ALERT_AREA)


async def test_areas_near_a_point(hass, aioclient_mock) -> None:
    aioclient_mock.get(
        AREAS_URL,
        params={"lat": "51.842", "long": "-2.637", "dist": "10"},
        json=load_fixture("flood_areas_near.json"),
    )

    areas = await get_flood_areas(async_get_clientsession(hass), 51.842, -2.637, 10)

    assert ALERT_AREA in [a.notation for a in areas]
    assert "031FWFVB10" in [a.notation for a in areas]


async def test_one_area(hass, aioclient_mock) -> None:
    aioclient_mock.get(
        f"{AREAS_URL}/{ALERT_AREA}", json=load_fixture("flood_area_031WAF120.json")
    )

    area = await get_flood_area(async_get_clientsession(hass), ALERT_AREA)

    assert area.label == "River Wye in Gloucestershire"
