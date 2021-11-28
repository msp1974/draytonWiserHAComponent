
from .const import (
    _LOGGER,
    DATA,
    DOMAIN,
    WISER_SERVICES,
    ATTR_TIME_PERIOD,
    DEFAULT_BOOST_TEMP_TIME,
    MANUFACTURER
)

from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
)
import voluptuous as vol
from homeassistant.helpers import config_validation as cv, entity_platform


ATTR_HW_MODE = "hotwater_mode"

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Wiser climate device."""
    data = hass.data[DOMAIN][config_entry.entry_id][DATA]  # Get Handler

    if data.wiserhub.hotwater:
        wiser_hot_water = [WiserHotWaterModeSelect(hass, data)]
        async_add_entities(wiser_hot_water, True)

    # Add SmartPlugs (if any)
    if data.wiserhub.devices.smartplugs.count > 0:
        wiser_smart_plugs = [
            WiserSmartPlugModeSelect(hass, data, plug.id)
            for plug in data.wiserhub.devices.smartplugs.all
        ]
        async_add_entities(wiser_smart_plugs)

    # Setup services
    platform = entity_platform.async_get_current_platform()

    if data.wiserhub.hotwater:
        platform.async_register_entity_service(
            WISER_SERVICES["SERVICE_SET_HOTWATER_MODE"],
            {
                vol.Required(ATTR_HW_MODE): vol.In(data.wiserhub.hotwater.available_modes),
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


class WiserSelectEntity(SelectEntity):
    def __init__(self, hass, data):
        """Initialize the sensor."""
        self.data = data
        self._hass = hass

    async def async_force_update(self):
        await self.data.async_update(no_throttle=True)

    @property
    def should_poll(self):
        """We don't want polling so return false."""
        return False

    @property
    def name(self):
        """Return Name of device."""
        return self._name

    @property
    def options(self) -> list[str]:
        return self._options

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


class WiserHotWaterModeSelect(WiserSelectEntity):

    def __init__(self, hass, data):
        """Initialize the sensor."""
        super().__init__(hass, data)
        self._hotwater = self.data.wiserhub.hotwater
        self._options = self._hotwater.available_modes

    async def async_update(self):
        """Async update method."""
        self._hotwater = self.data.wiserhub.hotwater
    
    @property
    def unique_id(self):
        """Return unique Id."""
        return f"{self.data.wiserhub.system.name}-WiserHotWaterModeSelect"

    @property
    def device_info(self):
        """Return device specific attributes."""
        identifier = f"{self.data.wiserhub.system.name}-WiserHotWater"
        return {
            "identifiers": {(DOMAIN, identifier)},
            "via_device": (DOMAIN, self.data.wiserhub.system.name),
        }

    @property
    def name(self):
        """Return Name of device."""
        return "Wiser Hot Water Mode"

    @property
    def current_option(self) -> str:
        return self._hotwater.mode

    def select_option(self, option: str) -> None:
        _LOGGER.debug("Setting hot water mode to {}".format(option))
        self._hotwater.mode = option
        self._hass.async_create_task(self.async_force_update())

    async def async_set_hotwater_mode(self, hotwater_mode):
        await self.hass.async_add_executor_job(
            self.select_option, hotwater_mode
        )

    async def async_boost_hotwater(self, time_period: int):
        await self.hass.async_add_executor_job(
            self.data.wiserhub.hotwater.boost, time_period
        )


class WiserSmartPlugModeSelect(WiserSelectEntity):

    def __init__(self, hass, data, smartplug_id):
        """Initialize the sensor."""
        super().__init__(hass, data)
        self._smartplug_id = smartplug_id
        self._smartplug = self.data.wiserhub.devices.smartplugs.get_by_id(self._smartplug_id)
        self._options = self._smartplug.available_modes

    async def async_update(self):
        """Async update method."""
        self._hotwater = self.data.wiserhub.devices.smartplugs.get_by_id(self._smartplug_id)
    
    @property
    def unique_id(self):
        """Return unique ID for the plug."""
        product_type = self._smartplug.product_type
        return f"{self.data.wiserhub.system.name}-{product_type}-{self._smartplug_id}-ModeSelect"

    @property
    def device_info(self):
        """Return device specific attributes."""
        product_type = self._smartplug.product_type
        identifier = f"{self.data.wiserhub.system.name}-{product_type}-{self._smartplug_id}"
        return {
            "identifiers": {(DOMAIN, identifier)},
            "via_device": (DOMAIN, self.data.wiserhub.system.name),
        }

    @property
    def name(self):
        """Return Name of device."""
        return f"Wiser {self._smartplug.name} Mode"

    @property
    def current_option(self) -> str:
        return self._smartplug.mode

    def select_option(self, option: str) -> None:
        _LOGGER.debug("Setting smartplug mode to {}".format(option))
        self._smartplug.mode = option
        self._hass.async_create_task(self.async_force_update())
