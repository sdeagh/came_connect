DOMAIN = "came_connect"
PLATFORMS = ["cover", "sensor", "binary_sensor", "button"]

# REST base
API_BASE = "https://app.cameconnect.net/api"

# OAuth / redirect
DEFAULT_REDIRECT_URI = "https://app.cameconnect.net/role"  # production default

# --- WebSocket (new push path) ---
DEFAULT_WEBSOCKET_URL = "wss://app.cameconnect.net/api/events-real-time"
CONF_USE_WEBSOCKET = "use_websocket"
CONF_WEBSOCKET_URL = "websocket_url"

# Config entry fields
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_REDIRECT_URI = "redirect_uri"
CONF_DEVICE_ID = "device_id"
CONF_BPT_KEYCODE = "bpt_keycode"
CONF_BPT_SIP_USER = "bpt_sip_user"
CONF_BPT_SIP_PASSWORD = "bpt_sip_password"
CONF_BPT_SIP_HA1 = "bpt_sip_ha1"
CONF_BPT_SRC_ADDR = "bpt_src_addr"
CONF_BPT_TARGET_USER = "bpt_target_user"
CONF_BPT_PANEL_ADDR = "bpt_panel_addr"
CONF_BPT_SUBJECT_LABEL = "bpt_subject_label"
CONF_BPT_DEVICE_TOKEN = "bpt_device_token"

# BPT SIP defaults
DEFAULT_BPT_TARGET_USER = "00800000000"
DEFAULT_BPT_PANEL_ADDR = "00e00000"
DEFAULT_BPT_APP_NAME = "com.came.myaccess"
DEFAULT_BPT_OS_TYPE = "android"
DEFAULT_BPT_LANG = "pt-PT"
DEFAULT_BPT_SIP_PROXY_HOST = "104.239.174.100"
DEFAULT_BPT_SIP_PROXY_PORT = 5061
DEFAULT_BPT_AUTH_PASSWORD_PREFIX = "BptX1pM0b1l3"

# Event / phase codes
PHASE_OPEN        = 16
PHASE_CLOSED      = 17
PHASE_OPENING     = 32
PHASE_CLOSING     = 33
PHASE_STOPPED      = 19  # seen when STOP mid-travel
EVENT_SNAPSHOT    = 23  # "ManeuverCountUpdate" / full snapshot
