import paho.mqtt.client as mqtt
import json
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EraMqttClient:
    """
    MQTT Client for connecting to E-Ra IoT Platform
    
    This client handles the connection to the E-Ra MQTT broker and provides
    methods for publishing alarm events when an intrusion is detected.
    """
    def __init__(self, broker="mqtt1.eoh.io", port=1883, token=None, device_uid=None):
        """
        Initialize the MQTT client with connection parameters
        
        Args:
            broker (str): MQTT broker address
            port (int): MQTT broker port
            token (str): Gateway token for authentication
            device_uid (str): Device UID for MQTT topics
        """
        self.broker = broker
        self.port = port
        self.token = token
        self.device_uid = device_uid
        self.client = mqtt.Client()
        self.connected = False
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        self.client.on_message = self._on_message
        
        # Set credentials if token is provided
        if self.token:
            # E-Ra expects the exact format: "Gateway <token>" without additional spaces
            self.client.username_pw_set(username=f"{self.token}", password=f"{self.token}")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker"""
        # MQTT Connection return codes:
        # 0: Connection successful
        # 1: Connection refused - incorrect protocol version
        # 2: Connection refused - invalid client identifier
        # 3: Connection refused - server unavailable
        # 4: Connection refused - bad username or password
        # 5: Connection refused - not authorized
        
        if rc == 0:
            self.connected = True
            logger.info("Connected to MQTT Broker")
            
            # Subscribe to control topic to receive commands from E-Ra
            if self.token and self.device_uid:
                control_topic = f"eoh/chip/{self.token}/third_party/{self.device_uid}/down"
                self.client.subscribe(control_topic)
                logger.info(f"Subscribed to control topic: {control_topic}")
                
            # Publish online status
            self._publish_online_status()
        else:
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error (code {rc})")
            logger.error(f"Failed to connect to MQTT broker: {error_msg}")
            
            # Debug information
            logger.debug(f"Connection details - Broker: {self.broker}, Port: {self.port}")
            logger.debug(f"Token format check - Length: {len(self.token) if self.token else 0}")
            if self.token:
                # Log a masked version of the token for security
                masked_token = self.token[:4] + "*" * (len(self.token) - 8) + self.token[-4:] if len(self.token) > 8 else "****"
                logger.debug(f"Using token: {masked_token}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the broker"""
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker with code {rc}")

    def _on_publish(self, client, userdata, mid):
        """Callback for when a message is published"""
        logger.debug(f"Message {mid} published successfully")

    def _on_message(self, client, userdata, msg):
        """Callback for when a message is received"""
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            logger.info(f"Received message on topic {msg.topic}: {payload}")
            
            # Handle incoming control messages here
            # This can be expanded based on your application needs
        except Exception as e:
            logger.error(f"Error processing received message: {e}")

    def _validate_credentials(self):
        """Validate the format of token and device_uid"""
        if not self.token:
            logger.error("Token is required for E-Ra IoT Platform")
            return False
            
        if not self.device_uid:
            logger.error("Device UID is required for E-Ra IoT Platform")
            return False
            
        # Log connection parameters for debugging
        logger.info(f"Connecting with - Broker: {self.broker}, Port: {self.port}")
        logger.info(f"Using token format: Gateway {self.token[:4]}...{self.token[-4:] if len(self.token) > 8 else ''}")
        logger.info(f"Using device_uid: {self.device_uid}")
        
        return True
            
    def connect(self):
        """Connect to the MQTT broker"""
        if not self._validate_credentials():
            return False
            
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            
            # Wait for connection to establish
            retry_count = 0
            while not self.connected and retry_count < 5:
                time.sleep(1)
                retry_count += 1
                
            if not self.connected:
                logger.error("Failed to connect after 5 retries")
                
            return self.connected
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    def disconnect(self):
        """Disconnect from the MQTT broker"""
        if self.connected:
            self._publish_offline_status()
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")

    def _publish_online_status(self):
        """Publish online status to the platform"""
        if self.token:
            online_topic = f"eoh/chip/{self.token}/is_online"
            payload = {"ol": 1}
            self.client.publish(online_topic, json.dumps(payload), qos=1, retain=True)
            logger.info(f"Published online status to {online_topic}")

    def _publish_offline_status(self):
        """Publish offline status to the platform"""
        if self.token:
            online_topic = f"eoh/chip/{self.token}/is_online"
            payload = {"ol": 0}
            self.client.publish(online_topic, json.dumps(payload), qos=1, retain=True)
            logger.info(f"Published offline status to {online_topic}")
    def publish_led_state(self, led_state):
        """Gửi trạng thái đèn LED đến E-Ra"""
        if not self.connected:
            return False
            
        try:
            topic = f"eoh/chip/{self.token}/third_party/{self.device_uid}/data"
            payload = {"config_led": led_state}
            self.client.publish(topic, json.dumps(payload), qos=1)
            return True
        except Exception as e:
            logger.error(f"Lỗi gửi trạng thái LED: {e}")
            return False
        
    def publish_intrusion_alert(self, alert_state=1):
        """
        Publish intrusion alert to E-Ra platform
        
        Args:
            alert_state (int): 1 for alarm activated, 0 for deactivated
        
        Returns:
            bool: True if published successfully, False otherwise
        """
        if not self.connected or not self.token or not self.device_uid:
            logger.error("Cannot publish alert: Not connected or missing credentials")
            return False
            
        try:
            # Format the topic according to E-Ra specifications
            topic = f"eoh/chip/{self.token}/third_party/{self.device_uid}/data"
            
            # Create the payload - when intrusion detected, set alarm to 1
            payload = {"config_led": alert_state}
            
            # Publish message
            result = self.client.publish(topic, json.dumps(payload), qos=1)
            result.wait_for_publish()
            
            if result.rc == 0:
                logger.info(f"Published intrusion alert to {topic}: {payload}")
                return True
            else:
                logger.error(f"Failed to publish intrusion alert, error code: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing intrusion alert: {e}")
            return False
        
    def publish_people_count(self, people_count):
        """
        Publish people count to E-Ra platform
        
        Args:
            people_count (int): Số lượng người trong khu vực
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
            """
        if not self.connected or not self.token or not self.device_uid:
            logger.error("Cannot publish people count: Not connected or missing credentials")
            return False
            
        try:
            topic = f"eoh/chip/{self.token}/third_party/{self.device_uid}/data"
            payload = {"config_peoplecount": people_count}  # Sử dụng đúng key config
            
            result = self.client.publish(topic, json.dumps(payload), qos=1)
            result.wait_for_publish()
            
            if result.rc == 0:
                logger.info(f"Published people count to {topic}: {payload}")
                return True
            else:
                logger.error(f"Failed to publish people count, error code: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing people count: {e}")
            return False