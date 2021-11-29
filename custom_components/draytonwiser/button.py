
from .const import (
    _LOGGER,
    DATA,
    DOMAIN,
    MANUFACTURER
)

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Wiser climate device."""
    data = hass.data[DOMAIN][config_entry.entry_id][DATA]  # Get Handler

    wiser_buttons = [
        WiserBoostAllHeatingButton(hass, data),
        WiserCancelHeatingOverridesButton(hass, data)
    ]

    if data.wiserhub.hotwater is not None:
        wiser_buttons.append(
            WiserBoostHotWaterButton(hass, data)
        )
        wiser_buttons.append(
            WiserCancelBoostHotWaterButton(hass, data)
        )
    async_add_entities(wiser_buttons, True)


class WiserButton(ButtonEntity):
    def __init__(self, hass, data):
        """Initialize the sensor."""
        self.data = data
        self._hass = hass

    async def async_force_update(self):
        await self.data.async_update(no_throttle=True)

    @property
    def unique_id(self):
        """Return unique Id."""
        return f'{self.data.wiserhub.system.name}-Wiser {self.name.replace(" ","")} Button'
    
    @property
    def device_info(self):
        """Return device specific attributes."""
        identifier = self.data.unique_id
        return {
            "identifiers": {(DOMAIN, identifier)},
            "via_device": (DOMAIN, self.data.wiserhub.system.name),
        }

    async def async_added_to_hass(self):
        """Call when the button is added to hass."""
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            self.__last_pressed = dt_util.parse_datetime(state.state)

        """Subscribe for update from the hub."""
        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        self.async_on_remove(
            async_dispatcher_connect(
                self._hass, "{}-HubUpdateMessage".format(self.data.wiserhub.system.name), async_update_state
            )
        )


class WiserBoostAllHeatingButton(WiserButton):
    def __init__(self, hass, data):
        super().__init__(hass, data)

    async def async_press(self):
        boost_time = self.data.boost_time
        boost_temp = self.data.boost_temp
        await self.hass.async_add_executor_job(
            self.data.wiserhub.system.boost_all_rooms, boost_temp, boost_time
        )
        await self.async_force_update()

    @property
    def name(self):
        return "Wiser Boost All Heating"
    

class WiserCancelHeatingOverridesButton(WiserButton):
    def __init__(self, hass, data):
        super().__init__(hass, data)

    async def async_press(self):
        await self.hass.async_add_executor_job(
            self.data.wiserhub.system.cancel_all_overrides
        )
        await self.async_force_update()

    @property
    def name(self):
        return "Wiser Cancel All Heating Overrides"


class WiserBoostHotWaterButton(WiserButton):
    def __init__(self, hass, data):
        super().__init__(hass, data)

    async def async_press(self):
        boost_time = self.data.hw_boost_time
        await self.hass.async_add_executor_job(
            self.data.wiserhub.hotwater.boost, boost_time
        )
        await self.async_force_update()

    @property
    def name(self):
        return "Wiser Boost Hot Water"

    @property
    def icon(self):
        return "mdi:timer"


class WiserCancelBoostHotWaterButton(WiserButton):
    def __init__(self, hass, data):
        super().__init__(hass, data)

    async def async_press(self):
        await self.hass.async_add_executor_job(
            self.data.wiserhub.hotwater.cancel_overrides
        )
        await self.async_force_update()

    @property
    def name(self):
        return "Wiser Cancel Boost Hot Water"

    @property
    def icon(self):
        return "mdi:timer-off"
