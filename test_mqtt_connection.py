"""
Test script for verifying MQTT connection to E-Ra IoT Platform
Run this script to check if your credentials work correctly
"""
import paho.mqtt.client as mqtt
import time
import sys
from config import MQTT_BROKER, MQTT_PORT, MQTT_TOKEN, DEVICE_UID

# Detailed connection callback
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected successfully to MQTT broker!")
        print(f"   Broker: {MQTT_BROKER}")
        print(f"   Port: {MQTT_PORT}")
        print(f"   Token used: {MQTT_TOKEN[:4]}...{MQTT_TOKEN[-4:]}")
        print(f"   Device UID: {DEVICE_UID}")
        
        # Test publishing online status
        topic = f"eoh/chip/{MQTT_TOKEN}/is_online"
        payload = '{"ol": 1}'
        print(f"\nPublishing to topic: {topic}")
        print(f"Payload: {payload}")
        result = client.publish(topic, payload, qos=1, retain=True)
        
        if result.rc == 0:
            print("✅ Published online status successfully!")
        else:
            print(f"❌ Failed to publish: {result.rc}")
    else:
        error_codes = {
            1: "Incorrect protocol version",
            2: "Invalid client identifier",
            3: "Server unavailable",
            4: "Bad username or password",
            5: "Not authorized"
        }
        error_msg = error_codes.get(rc, f"Unknown error code {rc}")
        print(f"❌ Connection failed: {error_msg}")
        print("\nTroubleshooting suggestions:")
        
        if rc == 4:
            print("- Check if your token is correct")
            print("- Make sure username format is exactly 'Gateway <token>'")
            print("- Make sure password format is exactly 'Gateway <token>'")
        elif rc == 5:
            print("- Your token appears valid but you don't have authorization")
            print("- Check if your Gateway is registered correctly in E-Ra platform")
            print("- Check if your token is still active")
        
        print("\nExact connection parameters used:")
        print(f"Username: 'Gateway {MQTT_TOKEN}'")
        print(f"Password: 'Gateway {MQTT_TOKEN}'")

# Create new client instance
print("🔄 Testing connection to E-Ra IoT MQTT broker...")
client = mqtt.Client()
client.on_connect = on_connect

# Set credentials
print(f"🔐 Setting credentials with token: {MQTT_TOKEN[:4]}...{MQTT_TOKEN[-4:]}")
client.username_pw_set(f"{MQTT_TOKEN}", f"{MQTT_TOKEN}")

try:
    print(f"🔌 Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    
    # Wait for connection and callback
    time.sleep(5)
    
    # Test publishing device data
    if client.is_connected():
        topic = f"eoh/chip/{MQTT_TOKEN}/third_party/{DEVICE_UID}/data"
        payload = '{"alarm": 1}'
        print(f"\nPublishing to topic: {topic}")
        print(f"Payload: {payload}")
        result = client.publish(topic, payload, qos=1)
        
        if result.rc == 0:
            print("✅ Published alarm data successfully!")
        else:
            print(f"❌ Failed to publish alarm: {result.rc}")
    
    client.loop_stop()
    client.disconnect()
    
except Exception as e:
    print(f"❌ Connection error: {e}")
    print("\nPossible causes:")
    print("- Network connectivity issues")
    print("- Incorrect broker address or port")
    print("- Firewall blocking MQTT traffic")
    sys.exit(1)