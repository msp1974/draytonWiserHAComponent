"""
Switch  Platform Device for Wiser Rooms.

https://github.com/asantaga/wiserHomeAssistantPlatform
Angelosantagata@gmail.com
"""
import asyncio
import voluptuous as vol

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import _LOGGER, DATA, DOMAIN, MANUFACTURER, WISER_SERVICES, WISER_SWITCHES

try:
    from homeassistant.components.switch import SwitchEntity
except ImportError:
    from homeassistant.components.switch import SwitchDevice as SwitchEntity

ATTR_PLUG_MODE = "plug_mode"
ATTR_HOTWATER_MODE = "hotwater_mode"

SET_PLUG_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_PLUG_MODE, default="Auto"): vol.Coerce(str),
    }
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Wiser System Switch entities."""
    data = hass.data[DOMAIN][config_entry.entry_id][DATA]  # Get Handler

    # Add System Switches
    wiser_switches = []
    for switch in WISER_SWITCHES:
        wiser_switches.append(
            WiserSwitch(data, switch["name"], switch["key"], switch["icon"])
        )

    async_add_entities(wiser_switches)

    # Add SmartPlugs (if any)
    if data.wiserhub.devices.smartplugs.count > 0:
        wiser_smart_plugs = [
            WiserSmartPlug(data, plug.id, "Wiser {}".format(plug.name))
            for plug in data.wiserhub.devices.smartplugs.all
        ]
        async_add_entities(wiser_smart_plugs)

    @callback
    def set_smartplug_mode(service):
        entity_id = service.data[ATTR_ENTITY_ID]
        smart_plug_mode = service.data[ATTR_PLUG_MODE]

        _LOGGER.debug(
            "Set Smartplug called - entity %s mode %s ", entity_id, smart_plug_mode,
        )

        for smart_plug in wiser_smart_plugs:

            if smart_plug.entity_id == entity_id:
                hass.async_create_task(smart_plug.set_smartplug_mode(smart_plug_mode))
            smart_plug.schedule_update_ha_state(True)
            break
    """
    @callback
    def set_hotwater_mode(service):
        hotwater_mode = service.data[ATTR_HOTWATER_MODE]
        hass.async_create_task(data.set_hotwater_mode(hotwater_mode))

    # Register Services
    """
    """
    hass.services.async_register(
        DOMAIN,
        WISER_SERVICES["SERVICE_SET_SMARTPLUG_MODE"],
        set_smartplug_mode,
        schema=SET_PLUG_MODE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        WISER_SERVICES["SERVICE_SET_HOTWATER_MODE"],
        set_hotwater_mode,
        schema=SET_HOTWATER_MODE_SCHEMA,
    )
    """
    return True


class WiserSwitch(SwitchEntity):
    """Switch to set the status of the Wiser Operation Mode (Away/Normal)."""

    def __init__(self, data, switchType, hubKey, icon):
        """Initialize the sensor."""
        _LOGGER.info("Wiser %s Switch Init", switchType)
        self.data = data
        self._hub_key = hubKey
        self._icon = icon
        self._switch_type = switchType
        self._away_temperature = None
        self._is_on = False

    async def async_force_update(self):
        await self.data.async_update(no_throttle=True)

    async def async_update(self):
        """Async Update to HA."""
        _LOGGER.debug("Wiser %s Switch Update requested", self._switch_type)
        self._is_on = getattr(self.data.wiserhub.system, self._hub_key)
        if self._switch_type == "Away Mode":
            self._away_temperature = self.data.wiserhub.system.away_mode_target_temperature

    @property
    def name(self):
        """Return the name of the Device."""
        return "Wiser " + self._switch_type

    @property
    def icon(self):
        """Return icon."""
        return self._icon

    @property
    def unique_id(self):
        """Return uniqueId."""
        return f"{self.data.wiserhub.system.name}-{self._switch_type}-{self.name}"

    @property
    def device_info(self):
        """Return device specific attributes."""
        identifier = self.data.unique_id

        return {
            "identifiers": {(DOMAIN, identifier)},
            "via": self.data.wiserhub.system.name,
        }

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def extra_state_attributes(self):
        """Return the device state attributes for the attribute card."""
        attrs = {}

        if self._switch_type == "Away Mode":
            attrs["AwayModeTemperature"] = self._away_temperature

        return attrs

    @property
    def is_on(self):
        """Return true if device is on."""
        _LOGGER.debug("%s: %s", self._switch_type, self._is_on)
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn the device on."""
        await self.hass.async_add_executor_job(
            setattr, self.data.wiserhub.system, self._hub_key, True
        )
        await self.async_force_update()
        return True

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        await self.hass.async_add_executor_job(
            setattr, self.data.wiserhub.system, self._hub_key, False
        )
        await self.async_force_update()
        return True

    async def async_added_to_hass(self):
        """Subscribe for update from the hub."""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, "{}-HubUpdateMessage".format(self.data.wiserhub.system.name), async_update_state
            )
        )


class WiserSmartPlug(SwitchEntity):
    """Plug SwitchEntity Class."""

    def __init__(self, data, plugId, name):
        """Initialize the sensor."""
        _LOGGER.info("Wiser %s SmartPlug Init", name)
        self.plug_name = name
        self.smart_plug_id = plugId
        self.data = data

    async def async_force_update(self):
        await asyncio.sleep(1)
        await self.data.async_update(no_throttle=True)

    async def async_update(self):
        """Async Update to HA."""
        _LOGGER.debug("Wiser %s Switch Update requested", self.plug_name)
        #self.data.schedules[str(self.entity_id)] = self.data.wiserhub.getSmartPlug(self.smart_plug_id).get("ScheduleId")

    @property
    def unique_id(self):
        """Return unique ID for the plug."""
        product_type = self.data.wiserhub.devices.smartplugs.get_by_id(self.smart_plug_id).product_type
        return f"{self.data.wiserhub.system.name}-{product_type}-{self.smart_plug_id}"

    @property
    def icon(self):
        """Return icon for the plug."""
        return "mdi:power-socket-uk"

    @property
    def device_info(self):
        """Return device specific attributes."""
        identifier = None
        model = None

        identifier = self.unique_id
        model = self.data.wiserhub.devices.smartplugs.get_by_id(self.smart_plug_id).model

        return {
            "name": self.plug_name,
            "identifiers": {(DOMAIN, identifier)},
            "manufacturer": MANUFACTURER,
            "model": model,
            "sw_version": self.data.wiserhub.devices.smartplugs.get_by_id(self.smart_plug_id).firmware_version
        }

    @property
    def name(self):
        """Return the name of the SmartPlug."""
        return self.plug_name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.data.wiserhub.devices.smartplugs.get_by_id(self.smart_plug_id).is_on

    @property
    def extra_state_attributes(self):
        """Return set of device state attributes."""
        attrs = {}
        device_data = self.data.wiserhub.devices.smartplugs.get_by_id(self.smart_plug_id)
        attrs["ManualState"] = device_data.manual_state
        attrs["Name"] = device_data.name
        attrs["Mode"] = device_data.mode
        attrs["AwayAction"] = device_data.away_action
        attrs["OutputState"] = "On" if device_data.is_on else "Off"
        attrs["ControlSource"] = device_data.control_source
        attrs["ScheduledState"] = device_data.scheduled_state
        return attrs

    async def async_turn_on(self, **kwargs):
        """Turn the device on."""
        await self.hass.async_add_executor_job(
            self.data.wiserhub.devices.smartplugs.get_by_id(self.smart_plug_id).turn_on
        )
        await self.async_force_update()
        return True

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        await self.hass.async_add_executor_job(
            self.data.wiserhub.devices.smartplugs.get_by_id(self.smart_plug_id).turn_off
        )
        await self.async_force_update()
        return True

    async def set_smartplug_mode(self, plug_mode):
        """Set the smartplug mode."""
        await self.hass.async_add_executor_job(
            self.data.wiserhub.devices.smartplugs.get_by_id(self.smart_plug_id).mode, plug_mode
        )
        await self.async_force_update()
        return True

    async def async_added_to_hass(self):
        """Subscribe for update from the hub."""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, "{}-HubUpdateMessage".format(self.data.wiserhub.system.name), async_update_state
            )
        )
