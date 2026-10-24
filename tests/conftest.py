"""Shared fixtures for the EAFM-Enhanced tests."""

import json
from pathlib import Path
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

FIXTURES = Path(__file__).parent / "fixtures"

# A flood warning area with a warning in force when the fixtures were captured
# (24 October 2026), and the alert area that covers Symonds Yat East.
WARNING_AREA = "122FWC045"
ALERT_AREA = "031WAF120"
LYDBROOK = "2320"

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def flood_area_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain="eafm_enhanced",
        title="North Sea at Scarborough - Sandside (flood warning area)",
        data={"flood_area": WARNING_AREA},
        unique_id=f"flood_area_{WARNING_AREA}",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def station_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain="eafm_enhanced",
        title="Lydbrook (2196)",
        data={"station": LYDBROOK},
        unique_id=LYDBROOK,
    )
    entry.add_to_hass(hass)
    return entry
