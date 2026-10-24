"""Tests for adding a river gauge or a flood warning area."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_RADIUS
from homeassistant.data_entry_flow import FlowResultType

from custom_components.eafm_enhanced.aioeafm_local import Station
from custom_components.eafm_enhanced.floods import FloodArea, FloodError
from tests.conftest import ALERT_AREA, LYDBROOK, load_fixture

FLOW = "custom_components.eafm_enhanced.config_flow"


def _areas() -> list[FloodArea]:
    return [
        FloodArea.from_api(i) for i in load_fixture("flood_areas_near.json")["items"]
    ]


@pytest.fixture(autouse=True)
def no_setup() -> Generator[None]:
    with patch("custom_components.eafm_enhanced.async_setup_entry", return_value=True):
        yield


@pytest.fixture
def mock_areas() -> Generator[AsyncMock]:
    with patch(f"{FLOW}.get_flood_areas", AsyncMock(return_value=_areas())) as mock:
        yield mock


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        "eafm_enhanced", context={"source": config_entries.SOURCE_USER}
    )


async def test_offers_a_gauge_or_a_flood_area(hass) -> None:
    result = await _start(hass)

    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["station", "flood_area"]


async def test_adds_a_river_gauge(hass) -> None:
    station = Station(load_fixture("station_2320.json")["items"])
    with (
        patch(f"{FLOW}.aioeafm.get_stations", AsyncMock(return_value=[station])),
        patch(f"{FLOW}.aioeafm.get_station", AsyncMock(return_value=station)),
    ):
        result = await _start(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "station"}
        )
        assert result["step_id"] == "station"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"station": LYDBROOK}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Lydbrook (2196)"
    assert result["data"] == {"station": LYDBROOK}


async def _to_flood_area(hass):
    result = await _start(hass)
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "flood_area"}
    )


async def test_flood_area_search_defaults_to_home(hass) -> None:
    hass.config.latitude = 51.81
    hass.config.longitude = -2.71

    result = await _to_flood_area(hass)

    defaults = {str(k): k.default() for k in result["data_schema"].schema if k.default}
    assert defaults[CONF_LATITUDE] == 51.81
    assert defaults[CONF_LONGITUDE] == -2.71
    assert defaults[CONF_RADIUS] == 10


async def test_adds_a_flood_area(hass, mock_areas) -> None:
    result = await _to_flood_area(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_LATITUDE: 51.842, CONF_LONGITUDE: -2.637, CONF_RADIUS: 10},
    )
    mock_areas.assert_awaited_once()
    assert mock_areas.await_args.args[1:] == (51.842, -2.637, 10)
    assert result["step_id"] == "pick_area"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"flood_area": ALERT_AREA}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "River Wye in Gloucestershire (flood alert area)"
    assert result["data"] == {"flood_area": ALERT_AREA}
    assert result["result"].unique_id == f"flood_area_{ALERT_AREA}"


async def test_no_areas_nearby(hass) -> None:
    with patch(f"{FLOW}.get_flood_areas", AsyncMock(return_value=[])):
        result = await _to_flood_area(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_LATITUDE: 55.0, CONF_LONGITUDE: -3.0, CONF_RADIUS: 1},
        )

    assert result["step_id"] == "flood_area"
    assert result["errors"] == {"base": "no_areas"}


async def test_flood_area_search_fails(hass) -> None:
    with patch(f"{FLOW}.get_flood_areas", AsyncMock(side_effect=FloodError("down"))):
        result = await _to_flood_area(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_LATITUDE: 51.842, CONF_LONGITUDE: -2.637, CONF_RADIUS: 10},
        )

    assert result["errors"] == {"base": "cannot_connect"}


async def test_same_flood_area_twice_aborts(hass, mock_areas) -> None:
    for expected in (FlowResultType.CREATE_ENTRY, FlowResultType.ABORT):
        result = await _to_flood_area(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_LATITUDE: 51.842, CONF_LONGITUDE: -2.637, CONF_RADIUS: 10},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"flood_area": ALERT_AREA}
        )
        assert result["type"] is expected
