
from .const import (
    _LOGGER,
    DATA,
    DOMAIN,
    WISER_SERVICES,
    ATTR_TIME_PERIOD,
    DEFAULT_BOOST_TEMP_TIME
)

from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
)
import voluptuous as vol
from homeassistant.helpers import config_validation as cv, entity_platform

from wiserHeatAPIv2.wiserhub import (
    WiserHotWaterModeEnum
)


OPERATION_MODES = [WiserHotWaterModeEnum.auto.value, WiserHotWaterModeEnum.on.value, WiserHotWaterModeEnum.off.value]
ATTR_HW_MODE = "hotwater_mode"

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Wiser climate device."""
    data = hass.data[DOMAIN][config_entry.entry_id][DATA]  # Get Handler

    if data.wiserhub.hotwater:
        wiser_hot_water = [WiserHotWater(hass, data)]
        async_add_entities(wiser_hot_water, True)

    # Setup services
    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        WISER_SERVICES["SERVICE_SET_HOTWATER_MODE"],
        {
            vol.Required(ATTR_HW_MODE): vol.In(OPERATION_MODES),
        },
        "async_set_hotwater_mode"
    )

    platform.async_register_entity_service(
        WISER_SERVICES["SERVICE_BOOST_HOTWATER"],
        {
            vol.Optional(ATTR_TIME_PERIOD, default=DEFAULT_BOOST_TEMP_TIME): vol.Coerce(int),
        },
        "async_boost_hotwater"
    )


class WiserHotWater(SelectEntity):

    def __init__(self, hass, data):
        """Initialize the sensor."""
        self.data = data
        self._hass = hass
        self._hotwater = self.data.wiserhub.hotwater
        self._options = OPERATION_MODES

    async def async_force_update(self):
        await self.data.async_update(no_throttle=True)

    async def async_update(self):
        """Async update method."""
        self._hotwater = self.data.wiserhub.hotwater

    @property
    def should_poll(self):
        """We don't want polling so return false."""
        return False
    
    @property
    def unique_id(self):
        """Return unique Id."""
        return f"{self.data.wiserhub.system.name}-WiserHotWater"

    @property
    def device_info(self):
        """Return device specific attributes."""
        identifier = self.data.unique_id
        return {
            "identifiers": {(DOMAIN, identifier)},
            "via_device": (DOMAIN, self.data.wiserhub.system.name),
        }

    @property
    def name(self):
        """Return Name of device."""
        return "Wiser Hot Water Mode"
    
    @property
    def options(self) -> list[str]:
        return self._options

    @property
    def current_option(self) -> str:
        return self._hotwater.mode.value

    def select_option(self, option: str) -> None:
        _LOGGER.info("Setting hot water mode to {}".format(option))
        self._hotwater.mode = WiserHotWaterModeEnum[option.lower()]
        self._hass.async_create_task(self.async_force_update())

    async def async_set_hotwater_mode(self, hotwater_mode):
        await self.hass.async_add_executor_job(
            self.select_option, hotwater_mode
        )

    async def async_boost_hotwater(self, time_period: int):
        await self.hass.async_add_executor_job(
            self.data.wiserhub.hotwater.boost, time_period
        )

    async def async_added_to_hass(self):
        """Subscribe for update from the hub."""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        self.async_on_remove(
            async_dispatcher_connect(
                self._hass, "{}-HubUpdateMessage".format(self.data.wiserhub.system.name), async_update_state
            )
        )