"""
Constants  for Wiser Platform.

https://github.com/asantaga/wiserHomeAssistantPlatform
Angelosantagata@gmail.com

"""
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "draytonwiser"
DATA_WISER_CONFIG = "wiser_config"
VERSION = "1.3.1"
WISER_PLATFORMS = ["climate", "sensor", "switch", "select"]
WISER_ADD_PLATFORMS = ["button"]
DATA = "data"
UPDATE_TRACK = "update_track"
UPDATE_LISTENER = "update_listener"

# Hub
HUBNAME = "Wiser Heat Hub"
MANUFACTURER = "Drayton Wiser"
ROOM = "Room"

# Notifications
NOTIFICATION_ID = "wiser_notification"
NOTIFICATION_TITLE = "Wiser Component Setup"

# Default Values
DEFAULT_BOOST_TEMP = 2
DEFAULT_BOOST_TEMP_TIME = 60
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_SETPOINT_MODE = "normal"

# Custom Configs
CONF_BOOST_TEMP = "boost_temp"
CONF_BOOST_TEMP_TIME = "boost_time"
CONF_SETPOINT_MODE = "setpoint_mode"

# Custom Attributes
ATTR_TIME_PERIOD = "time_period"

"""
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
WEEKENDS = ["saturday", "sunday"]
SPECIALDAYS = ["weekdays", "weekends"]
"""

WISER_SWITCHES = [
    {
        "name": "Valve Protection",
        "key": "valve_protection_enabled",
        "icon": "mdi:snowflake-alert",
    },
    {"name": "Eco Mode", "key": "eco_mode_enabled", "icon": "mdi:leaf"},
    {
        "name": "Away Mode Affects Hot Water",
        "key": "away_mode_affects_hotwater",
        "icon": "mdi:water",
    },
    {"name": "Comfort Mode", "key": "comfort_mode_enabled", "icon": "mdi:sofa"},
    {"name": "Away Mode", "key": "away_mode_enabled", "icon": "mdi:beach"},
    {"name": "Daylight Saving", "key": "automatic_daylight_saving_enabled", "icon": "mdi:clock-time-one" }  
]


SIGNAL_STRENGTH_ICONS = {
    "Online": "mdi:wifi-strength-4",
    "NoSignal": "mdi:wifi-strength-alert-outline",
    "Poor": "mdi:wifi-strength-1",
    "Medium": "mdi:wifi-strength-2",
    "Good": "mdi:wifi-strength-3",
    "VeryGood": "mdi:wifi-strength-4",
}

WISER_SERVICES = {
    "SERVICE_BOOST_HEATING": "boost_heating",
    "SERVICE_COPY_SCHEDULE": "copy_schedule",
    "SERVICE_GET_SCHEDULE": "get_schedule",
    "SERVICE_SET_SCHEDULE": "set_schedule",
    "SERVICE_SET_SMARTPLUG_MODE": "set_smartplug_mode",
    "SERVICE_SET_HOTWATER_MODE": "set_hotwater_mode",
    "SERVICE_BOOST_HOTWATER": "boost_hotwater",
}

WISER_BOOST_PRESETS = {
    "Boost 30m": 30,
    "Boost 1h": 60,
    "Boost 2h": 120,
    "Boost 3h": 180,
    "Cancel Boost": 0
}
