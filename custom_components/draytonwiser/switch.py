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

from .const import _LOGGER, DATA, DOMAIN, MANUFACTURER

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

WISER_SWITCHES = [
    {
        "name": "Valve Protection",
        "key":  "valve_protection_enabled",
        "icon": "mdi:snowflake-alert",
        "type": "system",
    },
    {
        "name": "Eco Mode", 
        "key":  "eco_mode_enabled", 
        "icon": "mdi:leaf",
        "type": "system",
    },
    {
        "name": "Away Mode Affects Hot Water",
        "key":  "away_mode_affects_hotwater",
        "icon": "mdi:water",
        "type": "system",
    },
    {
        "name": "Comfort Mode", 
        "key":  "comfort_mode_enabled", 
        "icon": "mdi:sofa",
        "type": "system",
    },
    {
        "name": "Away Mode",
        "key":  "away_mode_enabled",
        "icon": "mdi:beach",
        "type": "system",
    },
    {
        "name": "Daylight Saving",
        "key":  "automatic_daylight_saving_enabled", 
        "icon": "mdi:clock-time-one",
        "type": "system",
    },
    {
        "name": "Window Detection",
        "key":  "window_detection_active",
        "icon": "mdi:window-closed",
        "type": "room"
    },
]

WISER_ROOM_SWITCHES = [
    {
        "name": "Window Detection",
        "key": "window_detection_active",
        "icon": "mdi:window-closed",
    },
]



async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Wiser System Switch entities."""
    data = hass.data[DOMAIN][config_entry.entry_id][DATA]  # Get Handler

    # Add System Switches
    wiser_system_switches = []
    for switch in (switch for switch in WISER_SWITCHES if switch["type"] == "system"):
        wiser_system_switches.append(
            WiserSystemSwitch(data, switch["name"], switch["key"], switch["icon"])
        )
    async_add_entities(wiser_system_switches)


    # Add room switches
    wiser_room_switches = []
    if data.wiserhub.rooms.count > 0:
        for switch in (switch for switch in WISER_SWITCHES if switch["type"] == "room"):
            for room in data.wiserhub.rooms.all:
                if len(room.devices) > 0:
                    wiser_room_switches.append(
                        WiserRoomSwitch(data, switch["name"], switch["key"], switch["icon"], room.id )
                    )
        async_add_entities(wiser_room_switches)


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

    def __init__(self, data, name, key, icon):
        """Initialize the sensor."""
        _LOGGER.info("Wiser %s Switch Init", name)
        self.data = data
        self._key = key
        self._icon = icon
        self._name = name
        self._is_on = False
        self._away_temperature = None

    async def async_force_update(self):
        await self.data.async_update(no_throttle=True)

    @property
    def name(self):
        """Return the name of the Device."""
        return "Wiser " + self._name

    @property
    def icon(self):
        """Return icon."""
        return self._icon

    @property
    def unique_id(self):
        return f"{self.data.wiserhub.system.name}-{self._type}-switch-{self.name}"

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def is_on(self):
        """Return true if device is on."""
        _LOGGER.debug("%s: %s", self._name, self._is_on)
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn the device on."""
        raise NotImplemented

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        raise NotImplemented


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


class WiserSystemSwitch(WiserSwitch):
    """Switch to set the status of a system switch"""

    def __init__(self, data, name, key, icon):
        """Initialize the sensor."""
        super().__init__(data, name, key, icon)
        self._away_temperature = None

    async def async_update(self):
        """Async Update to HA."""
        _LOGGER.debug("Wiser %s Switch Update requested", self._name)
        self._is_on = getattr(self.data.wiserhub.system, self._key)
        if self._name == "Away Mode":
            self._away_temperature = self.data.wiserhub.system.away_mode_target_temperature

    async def async_turn_on(self, **kwargs):
        """Turn the device on."""
        await self.hass.async_add_executor_job(
            setattr, self.data.wiserhub.system, self._key, True
        )
        await self.async_force_update()
        return True

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        await self.hass.async_add_executor_job(
            setattr, self.data.wiserhub.system, self._key, False
        )
        await self.async_force_update()
        return True

    @property
    def unique_id(self):
        """Return uniqueId."""
        return f"{self.data.wiserhub.system.name}-system-switch-{self.name}"

    @property
    def extra_state_attributes(self):
        """Return the device state attributes for the attribute card."""
        attrs = {}

        if self._name == "Away Mode":
            attrs["AwayModeTemperature"] = self._away_temperature

        return attrs


class WiserHotWaterSwitch(WiserSwitch):
    """Switch to set the status of a hot water switch"""

    def __init__(self, data, name, key, icon):
        """Initialize the sensor."""
        super().__init__(data, name, key, icon)

    async def async_update(self):
        """Async Update to HA."""
        _LOGGER.debug("Wiser %s Switch Update requested", self._name)
        self._is_on = getattr(self.data.wiserhub.system, self._key)
        if self._name == "Away Mode":
            self._away_temperature = self.data.wiserhub.system.away_mode_target_temperature

    async def async_turn_on(self, **kwargs):
        """Turn the device on."""
        await self.hass.async_add_executor_job(
            setattr, self.data.wiserhub.system, self._key, True
        )
        await self.async_force_update()
        return True

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        await self.hass.async_add_executor_job(
            setattr, self.data.wiserhub.system, self._key, False
        )
        await self.async_force_update()
        return True

    @property
    def unique_id(self):
        """Return uniqueId."""
        return f"{self.data.wiserhub.system.name}-system-switch-{self.name}"

    @property
    def extra_state_attributes(self):
        """Return the device state attributes for the attribute card."""
        attrs = {}

        if self._name == "Away Mode":
            attrs["AwayModeTemperature"] = self._away_temperature

        return attrs


class WiserRoomSwitch(WiserSwitch):
    """Switch to set the status of a system switch"""

    def __init__(self, data, name, key, icon, room_id):
        """Initialize the sensor."""
        super().__init__(data, name, key, icon)
        self._room_id = room_id
        self._away_temperature = None

    async def async_update(self):
        """Async Update to HA."""
        _LOGGER.debug("Wiser %s Switch Update requested", self._name)
        self._is_on = getattr(self.data.wiserhub.rooms.get_by_id(self._room_id), self._key)

    @property
    def name(self):
        """Return the name of the Device."""
        return f"Wiser {self.data.wiserhub.rooms.get_by_id(self._room_id).name} {self._name}"

    async def async_turn_on(self, **kwargs):
        """Turn the device on."""
        await self.hass.async_add_executor_job(
            setattr, self.data.wiserhub.rooms.get_by_id(self._room_id), self._key, True
        )
        await self.async_force_update()
        return True

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        await self.hass.async_add_executor_job(
            setattr, self.data.wiserhub.rooms.get_by_id(self._room_id), self._key, False
        )
        await self.async_force_update()
        return True

    @property
    def unique_id(self):
        """Return unique Id."""
        return f"{self.data.wiserhub.system.name}-WiserRoom-{self._room_id}-{self._name}"

    @property
    def device_info(self):
        """Return device specific attributes."""
        identifier = f"{self.data.wiserhub.system.name}-WiserRoom-{self._room_id}-Wiser {self.data.wiserhub.rooms.get_by_id(self._room_id).name}"

        return {
            "identifiers": {(DOMAIN, identifier)},
            "via": self.data.wiserhub.system.name,
        }

    @property
    def extra_state_attributes(self):
        """Return the device state attributes for the attribute card."""
        attrs = {}
        return attrs


class WiserSmartPlug(WiserSwitch):
    """Plug SwitchEntity Class."""

    def __init__(self, data, plugId, name):
        """Initialize the sensor."""
        _LOGGER.info("Wiser %s SmartPlug Init", name)
        super().__init__(data, name, "", "mdi:power-socket-uk")
        self._name = name
        self.smart_plug_id = plugId
        self.data = data

    async def async_force_update(self):
        await asyncio.sleep(1)
        await self.data.async_update(no_throttle=True)

    async def async_update(self):
        """Async Update to HA."""
        _LOGGER.debug("Wiser %s Switch Update requested", self._name)
        self._is_on = self.data.wiserhub.devices.smartplugs.get_by_id(self.smart_plug_id).is_on

    @property
    def unique_id(self):
        """Return unique ID for the plug."""
        product_type = self.data.wiserhub.devices.smartplugs.get_by_id(self.smart_plug_id).product_type
        return f"{self.data.wiserhub.system.name}-{product_type}-{self.smart_plug_id}"

    @property
    def device_info(self):
        """Return device specific attributes."""
        identifier = None
        model = None

        identifier = self.unique_id
        model = self.data.wiserhub.devices.smartplugs.get_by_id(self.smart_plug_id).model

        return {
            "name": self._name,
            "identifiers": {(DOMAIN, identifier)},
            "manufacturer": MANUFACTURER,
            "model": model,
            "sw_version": self.data.wiserhub.devices.smartplugs.get_by_id(self.smart_plug_id).firmware_version
        }

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
