"""Tests for setting up gauges and flood warning areas end to end."""

from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.eafm_enhanced.floods import AREAS_URL, FLOODS_URL
from tests.conftest import LYDBROOK, WARNING_AREA, load_fixture

STATIONS_URL = "https://environment.data.gov.uk/flood-monitoring/id/stations"


def _mock_area(aioclient_mock, floods="floods_warning.json") -> None:
    aioclient_mock.get(
        f"{AREAS_URL}/{WARNING_AREA}", json=load_fixture("flood_area_warning.json")
    )
    aioclient_mock.get(
        FLOODS_URL, params={"floodArea": WARNING_AREA}, json=load_fixture(floods)
    )


def _entity(hass, unique_id: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        unique_id.split(":")[0], "eafm_enhanced", unique_id.split(":")[1]
    )
    assert entity_id, unique_id
    return entity_id


async def test_flood_area_entities(hass, flood_area_entry, aioclient_mock) -> None:
    _mock_area(aioclient_mock)

    assert await hass.config_entries.async_setup(flood_area_entry.entry_id)
    await hass.async_block_till_done()

    warning = hass.states.get(
        _entity(hass, f"sensor:flood_area_{WARNING_AREA}_warning")
    )
    in_force = hass.states.get(
        _entity(hass, f"binary_sensor:flood_area_{WARNING_AREA}_in_force")
    )
    assert warning.state == "flood_warning"
    assert warning.attributes["severity"] == "Flood warning"
    assert warning.attributes["message"]
    assert warning.attributes["area"] == "North Sea at Scarborough - Sandside"
    assert warning.attributes["url"].endswith(WARNING_AREA)
    assert in_force.state == "on"


async def test_flood_area_with_nothing_in_force(
    hass, flood_area_entry, aioclient_mock
) -> None:
    _mock_area(aioclient_mock, "floods_none.json")

    assert await hass.config_entries.async_setup(flood_area_entry.entry_id)
    await hass.async_block_till_done()

    warning = hass.states.get(
        _entity(hass, f"sensor:flood_area_{WARNING_AREA}_warning")
    )
    assert warning.state == "none"
    assert warning.attributes["message"] is None
    in_force = _entity(hass, f"binary_sensor:flood_area_{WARNING_AREA}_in_force")
    assert hass.states.get(in_force).state == "off"


async def test_flood_area_updates(hass, flood_area_entry, aioclient_mock) -> None:
    _mock_area(aioclient_mock, "floods_none.json")
    assert await hass.config_entries.async_setup(flood_area_entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.clear_requests()
    _mock_area(aioclient_mock, "floods_warning.json")
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
    await hass.async_block_till_done()

    warning = _entity(hass, f"sensor:flood_area_{WARNING_AREA}_warning")
    assert hass.states.get(warning).state == "flood_warning"


async def test_flood_area_retries_when_the_api_is_down(
    hass, flood_area_entry, aioclient_mock
) -> None:
    aioclient_mock.get(f"{AREAS_URL}/{WARNING_AREA}", status=503)

    await hass.config_entries.async_setup(flood_area_entry.entry_id)
    await hass.async_block_till_done()

    assert flood_area_entry.state is ConfigEntryState.SETUP_RETRY


async def test_flood_area_unloads(hass, flood_area_entry, aioclient_mock) -> None:
    _mock_area(aioclient_mock)
    assert await hass.config_entries.async_setup(flood_area_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(flood_area_entry.entry_id)
    assert flood_area_entry.state is ConfigEntryState.NOT_LOADED


async def test_river_gauge_still_works(hass, station_entry, aioclient_mock) -> None:
    aioclient_mock.get(
        f"{STATIONS_URL}/{LYDBROOK}", json=load_fixture("station_2320.json")
    )

    assert await hass.config_entries.async_setup(station_entry.entry_id)
    await hass.async_block_till_done()

    level = [
        s
        for s in hass.states.async_all("sensor")
        if s.attributes.get("river") == "River Wye"
    ]
    assert level
    assert level[0].attributes["typical_range_high"] == 4
    assert await hass.config_entries.async_unload(station_entry.entry_id)
