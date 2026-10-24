"""The EAFM-Enhanced integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .flood_entities import CONF_FLOOD_AREA, FloodAreaCoordinator
from .floods import FloodError, get_flood_area

PLATFORMS = [Platform.SENSOR]
FLOOD_AREA_PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


def _platforms(entry: ConfigEntry) -> list[Platform]:
    return FLOOD_AREA_PLATFORMS if CONF_FLOOD_AREA in entry.data else PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EAFM-Enhanced from a config entry."""
    if CONF_FLOOD_AREA in entry.data:
        session = async_get_clientsession(hass)
        try:
            area = await get_flood_area(session, entry.data[CONF_FLOOD_AREA])
        except FloodError as err:
            raise ConfigEntryNotReady(str(err)) from err
        coordinator = FloodAreaCoordinator(hass, entry, session, area)
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, _platforms(entry))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _platforms(entry))
