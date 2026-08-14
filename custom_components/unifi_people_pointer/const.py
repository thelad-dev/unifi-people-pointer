"""Constants for the UniFi People Pointer integration."""

DOMAIN = "unifi_people_pointer"

# Config Entry Keys
CONF_HOST = "host"
CONF_API_KEY = "api_key"
CONF_SITE_ID = "site_id"
CONF_VERIFY_SSL = "verify_ssl"
CONF_POLL_INTERVAL = "poll_interval"
CONF_GRACE_PERIOD = "grace_period"
CONF_ENABLE_MOBILE_APP_FALLBACK = "enable_mobile_app_fallback"
CONF_ENABLE_PING_FALLBACK = "enable_ping_fallback"
CONF_EVENT_DEBOUNCE = "event_debounce"
CONF_ENABLE_OUI_UPDATE = "enable_oui_update"
CONF_OUI_UPDATE_INTERVAL = "oui_update_interval"
CONF_OUI_SOURCE = "oui_source"

# Default Values
DEFAULT_SITE_ID = "default"
DEFAULT_VERIFY_SSL = True
DEFAULT_POLL_INTERVAL = 45
DEFAULT_GRACE_PERIOD = 600  # 10 minutes
DEFAULT_ENABLE_MOBILE_APP_FALLBACK = True
DEFAULT_ENABLE_PING_FALLBACK = True
DEFAULT_EVENT_DEBOUNCE = 180  # 3 minutes
DEFAULT_ENABLE_OUI_UPDATE = True
DEFAULT_OUI_UPDATE_INTERVAL = "monthly"
DEFAULT_OUI_SOURCE = "https://standards-oui.ieee.org/oui/oui.txt"

# Min/Max Values
MIN_POLL_INTERVAL = 10
MAX_POLL_INTERVAL = 600
MIN_GRACE_PERIOD = 60
MAX_GRACE_PERIOD = 1800
MIN_EVENT_DEBOUNCE = 0
MAX_EVENT_DEBOUNCE = 600

# Events
EVENT_PERSON_ARRIVED = "unifi_people_pointer_person_arrived"
EVENT_PERSON_LEFT = "unifi_people_pointer_person_left"
EVENT_DEVICE_CONNECTED = "unifi_people_pointer_device_connected"
EVENT_UNKNOWN_DEVICE = "unifi_people_pointer_unknown_device"

# Storage
STORAGE_DIR = "unifi_people_pointer"
PEOPLE_FILE = "people.json"
DEVICES_FILE = "devices.json"
AP_ZONES_FILE = "ap_zones.json"
MANUFACTURERS_FILE = "manufacturers.json"
OUI_VENDORS_FILE = "oui_vendors.json"

# Auto-dismiss
AUTO_DISMISS_DAYS = 7

# Platforms
PLATFORMS = ["device_tracker", "sensor"]
