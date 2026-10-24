"""Config flow for EAFM-Enhanced integration."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_RADIUS
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from . import aioeafm_local as aioeafm
from .flood_entities import CONF_FLOOD_AREA
from .floods import FloodError, get_flood_areas

DEFAULT_SEARCH_KM = 10

_LOGGER = logging.getLogger(__name__)

class EafmConfigFlow(config_entries.ConfigFlow, domain="eafm_enhanced"):
    """Handle a config flow for EAFM-Enhanced."""

    VERSION = 1

    def __init__(self):
        self._areas = {}

    async def async_step_user(self, user_input=None):
        """Choose what to add: a river gauge or a flood warning area."""
        return self.async_show_menu(
            step_id="user", menu_options=["station", "flood_area"]
        )

    async def async_step_flood_area(self, user_input=None):
        """Find EA flood alert and warning areas near a point."""
        errors = {}
        if user_input is not None:
            try:
                areas = await get_flood_areas(
                    async_get_clientsession(self.hass),
                    user_input[CONF_LATITUDE],
                    user_input[CONF_LONGITUDE],
                    user_input[CONF_RADIUS],
                )
            except FloodError:
                _LOGGER.exception("Couldn't search for flood areas")
                errors["base"] = "cannot_connect"
            else:
                if areas:
                    self._areas = {a.notation: a for a in areas}
                    return await self.async_step_pick_area()
                errors["base"] = "no_areas"

        defaults = user_input or {}
        return self.async_show_form(
            step_id="flood_area",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_LATITUDE,
                    default=defaults.get(CONF_LATITUDE, self.hass.config.latitude),
                ): cv.latitude,
                vol.Required(
                    CONF_LONGITUDE,
                    default=defaults.get(CONF_LONGITUDE, self.hass.config.longitude),
                ): cv.longitude,
                vol.Required(
                    CONF_RADIUS, default=defaults.get(CONF_RADIUS, DEFAULT_SEARCH_KM)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=50, unit_of_measurement="km",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }),
            errors=errors,
        )

    async def async_step_pick_area(self, user_input=None):
        """Pick one of the areas found."""
        if user_input is not None:
            area = self._areas[user_input[CONF_FLOOD_AREA]]
            await self.async_set_unique_id(f"flood_area_{area.notation}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"{area.label} ({area.kind})",
                data={CONF_FLOOD_AREA: area.notation},
            )

        choices = {
            a.notation: f"{a.label} ({a.kind})"
            for a in sorted(self._areas.values(), key=lambda a: a.label)
        }
        return self.async_show_form(
            step_id="pick_area",
            data_schema=vol.Schema({vol.Required(CONF_FLOOD_AREA): vol.In(choices)}),
        )

    async def async_step_station(self, user_input=None):
        """Add a river gauge (monitoring station)."""
        errors = {}

        if user_input is not None:
            # We need the station object to get the Label and RLOI for the title
            session = async_get_clientsession(self.hass)
            station = await aioeafm.get_station(session, user_input["station"])
            
            # Formatting the title: Label (RLOIid)
            name_id = station.rloi_id if station and station.rloi_id else user_input["station"]
            display_title = f"{station.label} ({name_id})" if station else f"Station {user_input['station']}"

            await self.async_set_unique_id(user_input["station"])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=display_title, 
                data=user_input
            )

        session = async_get_clientsession(self.hass)
        try:
            all_stations = await aioeafm.get_stations(session)
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "cannot_connect"
            return self.async_abort(reason="cannot_connect")

        stations_dropdown = {}
        for station in all_stations:
            display_name = f"{station.label}, {station.catchment_name}"
            if station.rloi_id:
                display_name += f" ({station.rloi_id})"
            
            # Key by notation: unlike stationReference it is unique and can
            # always be looked up directly.
            stations_dropdown[station.notation] = display_name
        
        sorted_stations = dict(sorted(stations_dropdown.items(), key=lambda item: item[1]))

        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema({
                vol.Required("station"): vol.In(sorted_stations),
            }),
            errors=errors,
        )