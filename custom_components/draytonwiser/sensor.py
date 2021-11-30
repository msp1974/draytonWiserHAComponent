"""
Sensor Platform Device for Wiser System.

https://github.com/asantaga/wiserHomeAssistantPlatform
Angelosantagata@gmail.com

"""
from datetime import datetime
from homeassistant.const import ATTR_BATTERY_LEVEL, DEVICE_CLASS_BATTERY
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import config_validation as cv, entity_platform, service
import voluptuous as vol

from .const import (
    _LOGGER,
    DATA,
    DOMAIN,
    MANUFACTURER,
    SIGNAL_STRENGTH_ICONS,
)

CONF_HUB_ID = "wiser_hub_id"
SERVICE_REMOVE_ORPHANED_ENTRIES = "remove_orphaned_entries"
SELECT_HUB_SCHEMA = vol.All(vol.Schema({vol.Optional(CONF_HUB_ID): str}))



async def async_setup_entry(hass, config_entry, async_add_entities):
    """Initialize the entry."""
    data = hass.data[DOMAIN][config_entry.entry_id][DATA]  # Get Handler
    wiser_devices = []
    hub_devices = data.wiserhub.devices.all

    # Add device sensors for all devices
    if data.wiserhub.devices.count > 0:
        for device in data.wiserhub.devices.all:
            wiser_devices.append(
                WiserDeviceSensor(data, device.id, device.product_type)
            )
            if device.product_type in ["iTRV", "RoomStat"]:
                wiser_devices.append(
                        WiserBatterySensor(data, device.id, sensor_type="Battery")
                )
    
    # Add cloud status sensor
    wiser_devices.append(WiserSystemCloudSensor(data, sensor_type="Cloud Sensor"))

    # Add operation sensor
    wiser_devices.append(
        WiserSystemOperationModeSensor(data, sensor_type="Operation Mode")
    )
    # Add heating circuit sensor
    if data.wiserhub.heating_channels.count > 0:
        for heating_channel in data.wiserhub.heating_channels.all:
                wiser_devices.append(
                    WiserSystemCircuitState(data, heating_channel.id, sensor_type="Heating")
                )
    
    # Don't display Hotwater if hotwater not supported
    # https://github.com/asantaga/wiserHomeAssistantPlatform/issues/8
    if data.wiserhub.hotwater is not None:
        wiser_devices.append(WiserSystemCircuitState(data, sensor_type="HotWater"))

    async_add_entities(wiser_devices, True)


class WiserSensor(Entity):
    """Definition of a Wiser sensor."""

    def __init__(self, config_entry, device_id=0, sensor_type=""):
        """Initialize the sensor."""
        self.data = config_entry
        self._device_id = device_id
        self._device_name = None
        self._sensor_type = sensor_type
        self._state = None

    async def async_update(self):
        """Async Update."""
        _LOGGER.debug("%s device update requested", self._device_name)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._device_name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        _LOGGER.debug("%s device state requested", self.name)
        return self._state

    @property
    def unique_id(self):
        """Return uniqueid."""
        return f"{self.data.wiserhub.system.name}-{self._sensor_type}-{self._device_id}"

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


class WiserBatterySensor(WiserSensor):
    """Definition of a battery sensor for wiser iTRVs and RoomStats."""

    def __init__(self, data, device_id=0, sensor_type=""):
        """Initialise the battery sensor."""

        super().__init__(data, device_id, sensor_type)
        self._device_name = self.get_device_name()
        self._state = "Unknown"
        self._battery_voltage = 0
        self._battery_level = None
        _LOGGER.info("%s device init", self._device_name)

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self.data.wiserhub.devices.get_by_id(self._device_id).battery.percent

    @property
    def device_class(self):
        """Return the class of the sensor."""
        return DEVICE_CLASS_BATTERY

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity."""
        return "%"

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the battery."""
        attrs = {}
        device = self.data.wiserhub.devices.get_by_id(self._device_id)
        attrs["battery_voltage"] = device.battery.voltage
        attrs[ATTR_BATTERY_LEVEL] = device.battery.level
        return attrs

    def get_device_name(self):
        """Return the name of the Device."""
        product_type = str(
            self.data.wiserhub.devices.get_by_id(self._device_id).product_type or ""
        )

        # Only iTRVs and RoomStats have batteries
        if product_type in ["iTRV", "RoomStat"]:
            # Multiple ones get automagically number _n by HA
            device_name = (
                "Wiser "
                + product_type
                + "-"
                + self.data.wiserhub.rooms.get_by_device_id(self._device_id).name
                + " Battery Level"
            )
        else:
            device_name = (
                "Wiser "
                + product_type
                + "-"
                + str(
                    self.data.wiserhub.devices.get_by_id(self._device_id).serial_number
                    or "" + " Battery Level"
                )
            )
        return device_name
    
    @property
    def device_info(self):
        """Return device specific attributes."""
        product_type = self.data.wiserhub.devices.get_by_id(self._device_id).product_type
        info =  {
            "identifiers": {(DOMAIN, f"{self.data.wiserhub.system.name}-{product_type}-{self._device_id}")},
            "via_device": (DOMAIN, self.data.wiserhub.system.name),
        }
        return info


class WiserDeviceSensor(WiserSensor):
    """Definition of Wiser Device Sensor."""

    def __init__(self, data, device_id=0, sensor_type=""):
        """Initialise the device sensor."""

        super().__init__(data, device_id, sensor_type)
        self._device_name = self.get_device_name()
        self._battery_voltage = 0
        self._battery_level = None
        self._battery_percent = 0
        _LOGGER.info("%s device init", self._device_name)

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self.data.wiserhub.devices.get_by_id(self._device_id).signal.displayed_signal_strength

    @property
    def device_info(self):
        """Return device specific attributes."""
        info = {
            "name": self.name,
            "identifiers": {(DOMAIN, self.unique_id)},
            "manufacturer": MANUFACTURER,
            "model": self.data.wiserhub.devices.get_by_id(self._device_id).product_type,
            "sw_version": self.data.wiserhub.devices.get_by_id(self._device_id).firmware_version,
            "via_device": (DOMAIN, self.data.wiserhub.system.name),
        }
        return info

    def get_device_name(self):
        """Return the name of the Device."""
        product_type = str(
            self.data.wiserhub.devices.get_by_id(self._device_id).product_type or ""
        )

        if product_type == "Controller":
            device_name = f"Wiser Heathub"  # Only ever one of these per instance
        elif product_type in ["iTRV","RoomStat"]:
            # Multiple ones get automagically number _n by HA
            _LOGGER.info(self.data.wiserhub.rooms.get_by_device_id(self._device_id))
            device_name = (
                "Wiser "
                + product_type
                + "-"
                + self.data.wiserhub.rooms.get_by_device_id(self._device_id).name
            )
        elif product_type == "SmartPlug":
            device_name = (
                "Wiser " + self.data.wiserhub.devices.smartplugs.get_by_id(self._device_id).name
            )
        else:
            device_name = (
                "Wiser "
                + product_type
                + "-"
                + str(
                    self.data.wiserhub.devices.get_by_id(self._device_id).serial_number
                    or ""
                )
            )
        return device_name

    @property
    def icon(self):
        """Return icon for signal strength."""
        try:
            return SIGNAL_STRENGTH_ICONS[
                self.data.wiserhub.devices.get_by_id(self._device_id).signal.displayed_signal_strength
            ]
        except KeyError:
            # Handle anything else as no signal
            return SIGNAL_STRENGTH_ICONS["NoSignal"]

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        _LOGGER.debug("State attributes for %s %s", self._device_id, self._sensor_type)
        attrs = {}
        device_data = self.data.wiserhub.devices.get_by_id(self._device_id)

        # Generic attributes
        attrs["vendor"] = MANUFACTURER
        attrs["product_type"] = device_data.product_type
        attrs["model_identifier"] = device_data.model
        attrs["displayed_signal_strength"] = device_data.signal.displayed_signal_strength
        attrs["firmware"] = device_data.firmware_version
        attrs["serial_number"] = device_data.serial_number

        # if controller then add the zigbee data to the controller info
        attrs["zigbee_channel"] = (
            self.data.wiserhub.system.zigbee.network_channel
        )
        attrs["last_updated"] = datetime.now()

        # Network Data
        attrs["node_id"] = device_data.node_id
        attrs["displayed_signal_strength"] = device_data.signal.displayed_signal_strength

        if self._sensor_type in ["RoomStat", "iTRV"]:
            attrs["parent_node_id"] = device_data.parent_node_id
            # hub route
            if device_data.parent_node_id == 0:
                attrs["hub_route"] = "direct"
            else:
                attrs["hub_route"] = "repeater"
                attrs["repeater"] = self.data.wiserhub.devices.get_by_node_id(device_data.parent_node_id).name


        if device_data.signal.device_reception_rssi is not None:
            attrs["device_reception_RSSI"] = device_data.signal.device_reception_rssi
            attrs["device_reception_LQI"] = device_data.signal.device_reception_lqi

        if device_data.signal.controller_reception_rssi is not None:
            attrs["controller_reception_RSSI"] = device_data.signal.controller_reception_rssi
            attrs["device_reception_LQI"] = device_data.signal.controller_reception_lqi

        # Other
        if self._sensor_type == "RoomStat":
            attrs["humidity"] = self.data.wiserhub.devices.roomstats.get_by_id(self._device_id).current_humidity
            attrs["temperature"] = self.data.wiserhub.devices.roomstats.get_by_id(self._device_id).current_temperature
        return attrs


class WiserSystemCircuitState(WiserSensor):
    """Definition of a Hotwater/Heating circuit state sensor."""

    def __init__(self, data, device_id=0, sensor_type=""):
        """Initialise the CircuitState Sensor."""

        super().__init__(data, device_id, sensor_type)
        self._device_name = self.get_device_name()
        _LOGGER.info("%s device init", self._device_name)

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        if self._sensor_type == "Heating":
            self._state = self.data.wiserhub.heating_channels.get_by_id(self._device_id).heating_relay_status
        else:
            if self.data.wiserhub.hotwater.is_boosted:
                self._state = "Boosted"
            else:
                self._state = self.data.wiserhub.hotwater.current_state

    @property
    def device_info(self):
        """Return device specific attributes."""
        identifier = self.data.unique_id
        return {
            "identifiers": {(DOMAIN, identifier)},
            "via_device": (DOMAIN, self.data.wiserhub.system.name),
        }

    def get_device_name(self):
        """Return the name of the Device."""
        if self._sensor_type == "Heating":
            if self.data.wiserhub.heating_channels.count > 1:
                return "Wiser Heating Channel " + self._device_id
            else:
                return "Wiser Heating"
        return "Wiser Hot Water"

    @property
    def icon(self):
        """Return icon."""
        if self._sensor_type == "Heating":
            if self._state == "Off":
                return "mdi:radiator-disabled"
            return "mdi:radiator"

        # Hot water circuit
        if self._state == "Off":
            return "mdi:water-off"
        return "mdi:water"

    @property
    def extra_state_attributes(self):
        """Return additional info."""
        attrs = {}
        if self._sensor_type == "Heating":
            heating_channel = self.data.wiserhub.heating_channels.get_by_id(self._device_id)
            attrs[f"percentage_demand_{heating_channel.name}"] = heating_channel.percentage_demand
            attrs[f"room_ids_{heating_channel.name}"] = heating_channel.room_ids
            attrs[f"is_smartvalve_preventing_demand_{heating_channel.name}"] = heating_channel.is_smart_valve_preventing_demand
        else:
            hw = self.data.wiserhub.hotwater
            # If boosted show boost end time
            if hw.is_boosted:
                attrs["boost_end"] = hw.boost_end_time
            attrs["boost_time_remaining"] = int(hw.boost_time_remaining/60)
            attrs["away_mode_supressed"] = hw.away_mode_suppressed
            attrs["next schedule change"] = str(hw.schedule.next.time)
            attrs["next_schedule_state"] = hw.schedule.next.setting
            attrs["is_boosted"] = hw.is_boosted
        return attrs


class WiserSystemCloudSensor(WiserSensor):
    """Sensor to display the status of the Wiser Cloud."""

    def __init__(self, data, device_id=0, sensor_type=""):
        """Initialise the cloud sensor."""

        super().__init__(data, device_id, sensor_type)
        self._device_name = "Wiser Cloud Status"
        _LOGGER.info("%s device init", self._device_name)

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self.data.wiserhub.system.cloud.connection_status

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "identifiers": {(DOMAIN, self.data.unique_id)},
            "via_device": (DOMAIN, self.data.wiserhub.system.name),
        }

    @property
    def icon(self):
        """Return icon."""
        if self._state == "Connected":
            return "mdi:cloud-check"
        return "mdi:cloud-alert"


class WiserSystemOperationModeSensor(WiserSensor):
    """Sensor for the Wiser Operation Mode (Away/Normal etc)."""

    def __init__(self, data, device_id=0, sensor_type=""):
        """Initialise the operation mode sensor."""

        super().__init__(data, device_id, sensor_type)
        self._device_name = "Wiser Operation Mode"
        #self._override_type = self.data.wiserhub.getSystem().get("OverrideType")
        self._away_temperature = self.data.wiserhub.system.away_mode_target_temperature
        _LOGGER.info("%s device init", self._device_name)

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        #self._override_type = self.data.wiserhub.getSystem().get("OverrideType")
        self._away_temperature = self.data.wiserhub.system.away_mode_target_temperature
        self._state = self.mode()

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "identifiers": {(DOMAIN, self.data.unique_id)},
            "via_device": (DOMAIN, self.data.wiserhub.system.name),
        }

    def mode(self):
        """Return mode."""
        if self.data.wiserhub.system.is_away_mode_enabled:
            return "Away"
        return "Normal"

    @property
    def icon(self):
        """Return icon."""
        if self.mode() == "Normal":
            return "mdi:check"
        return "mdi:alert"

    @property
    def extra_state_attributes(self):
        """Return the device state attributes."""
        attrs = {"AwayModeTemperature": self._away_temperature}
        return attrs
