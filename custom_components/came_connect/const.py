
DOMAIN = "came_connect"
PLATFORMS = ["cover", "sensor", "binary_sensor"]

DEFAULT_REDIRECT_URI = "https://beta.cameconnect.net/role"  # tested with ZLX24SA board
DEFAULT_POLL_INTERVAL = 5  # seconds

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_REDIRECT_URI = "redirect_uri"
CONF_DEVICE_ID = "device_id"
CONF_POLL_INTERVAL = "poll_interval"

API_BASE = "https://app.cameconnect.net/api"

PHASE_OPEN        = 16
PHASE_CLOSED      = 17
PHASE_OPENING     = 32
PHASE_CLOSING     = 33
PHASE_PAUSED      = 19  # seen when STOP mid-travel

