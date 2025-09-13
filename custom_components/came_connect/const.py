DOMAIN = "came_connect"
PLATFORMS = ["cover", "sensor", "binary_sensor"]

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

# Event / phase codes
PHASE_OPEN        = 16
PHASE_CLOSED      = 17
PHASE_OPENING     = 32
PHASE_CLOSING     = 33
PHASE_STOPPED      = 19  # seen when STOP mid-travel
EVENT_SNAPSHOT    = 23  # "ManeuverCountUpdate" / full snapshot
