# Configuration file for E-Ra IoT Platform integration
# Update these values with your actual credentials

# E-Ra MQTT Broker settings
MQTT_BROKER = "mqtt1.eoh.io"
MQTT_PORT = 1883

# Replace with your actual token from E-Ra IoT Platform
# This is used for both username and password authentication
MQTT_TOKEN = "____your_token____"

# Replace with your actual device UID from E-Ra IoT Platform
# This is used in the MQTT topics
DEVICE_UID = "____your_device_uid____"

# Telegram settings (if used)
TELEGRAM_TOKEN = "____your_telegram_token____"
TELEGRAM_CHAT_ID = "____your_telegram_chat_id____"

# Detection settings
CONFIDENCE_THRESHOLD = 0.5
ALERT_COOLDOWN_SECONDS = 15  # Minimum time between alerts