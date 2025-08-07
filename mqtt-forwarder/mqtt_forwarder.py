# cd C:\Users\nguye\Downloads\PECC2\confluent-mqtt
#docker-compose down   
#docker-compose build
#docker-compose up -d --build
# docker compose up -d
#docker-compose logs -f spark 

## 1. Compute timestamp
#$ts = Get-Date -UFormat %s

# 2. Run mosquitto_pub inside the Mosquitto container
#docker run --rm --network mqtt-kafka-net eclipse-mosquitto `
#  mosquitto_pub -h mosquitto -t modbus/sensor1 `
#    -m "{\"device_id\":\"sensor1\",\"V_L1\":230,\"I_L1\":5,\"VA_L1\":1150,\"P_L1\":1035,\"timestamp\":$ts}"



#$ts = Get-Date -UFormat %s
#$payload = '{"device_id":"sensor1","V_L1":230,"I_L1":5,"VA_L1":1150,"P_L1":1035,"timestamp":' + $ts + '}'

#docker run --rm --network mqtt-kafka-net eclipse-mosquitto `
  #mosquitto_pub -h mosquitto -t modbus/sensor1 -m $payload


#docker exec -it kafka bash
#kafka-console-consumer --bootstrap-server localhost:9092 --topic modbus_sensor1 --from-beginning


#kafka-topics --bootstrap-server localhost:9092 \--create --topic modbus-data --partitions 1 --replication-factor 1


# Fixed Modbus-to-MQTT Forwarder
import time, datetime, struct, signal, sys, json
from pymodbus.client import ModbusTcpClient
import paho.mqtt.client as mqtt

# ─── CONFIG ──────────────────────────────────────────────
MODBUS_HOST   = "modbus-simulator"
MODBUS_PORT   = 502
SLAVE_ID      = 1

MQTT_BROKER   = "mosquitto"
MQTT_PORT     = 1883
MQTT_TOPIC    = "modbus/sensor1"

POLL_INTERVAL = 2  # seconds

# ─── HELPER ───────────────────────────────────────────────
def regs_to_float(high, low):
    try:
        b = high.to_bytes(2, 'big') + low.to_bytes(2, 'big')
        return struct.unpack('>f', b)[0]
    except Exception as e:
        print("Error converting registers to float:", e)
        return None

# ─── SETUP CLIENTS ─────────────────────────────────────────
modbus_client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
if not modbus_client.connect():
    print("Cannot connect to Modbus at", MODBUS_HOST, MODBUS_PORT)
    sys.exit(1)

mqtt_client = mqtt.Client()
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()
except Exception as e:
    print("Failed to connect to MQTT broker:", e)
    sys.exit(1)

stop = False
def on_signal(sig, frame):
    global stop
    stop = True
signal.signal(signal.SIGINT, on_signal)
signal.signal(signal.SIGTERM, on_signal)

print("▶️ Starting forwarder (Modbus → MQTT)...")

while not stop:
    try:
        # Read values from Modbus simulator
        rr_v  = modbus_client.read_holding_registers(address=1,  count=2, slave=SLAVE_ID)
        rr_i  = modbus_client.read_holding_registers(address=13, count=2, slave=SLAVE_ID)
        rr_va = modbus_client.read_holding_registers(address=19, count=2, slave=SLAVE_ID)
        rr_p  = modbus_client.read_holding_registers(address=25, count=2, slave=SLAVE_ID)


        if rr_v.isError() or rr_i.isError() or rr_va.isError() or rr_p.isError():
            print("⚠️ One or more Modbus read errors")
            time.sleep(POLL_INTERVAL)
            continue

        V  = regs_to_float(rr_v.registers[0], rr_v.registers[1])
        I  = regs_to_float(rr_i.registers[0], rr_i.registers[1])
        VA = regs_to_float(rr_va.registers[0], rr_va.registers[1])
        P  = regs_to_float(rr_p.registers[0], rr_p.registers[1])

        payload = {
            "device_id": "sensor1",
            "V_L1": round(V, 2) if V else None,
            "I_L1": round(I, 2) if I else None,
            "VA_L1": round(VA, 2) if VA else None,
            "P_L1": round(P, 2) if P else None,
            "timestamp": int(time.time())

        }

        result = mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
        status = result[0]
        if status == 0:
            print("Published to MQTT:", payload)
        else:
            print("Failed to publish to MQTT, status:", status)

    except Exception as e:
        print("Unexpected error:", e)

    time.sleep(POLL_INTERVAL)

print("Stopping forwarder...")
modbus_client.close()
mqtt_client.disconnect()
