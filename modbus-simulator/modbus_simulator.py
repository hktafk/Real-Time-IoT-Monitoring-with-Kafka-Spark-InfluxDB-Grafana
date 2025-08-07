# File: modbus_simulator.py

from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading, time, struct, nest_asyncio, json, paho.mqtt.client as mqtt

nest_asyncio.apply()

#CONFIG 
SLAVE_ID    = 1
MQTT_BROKER = "mosquitto"
MQTT_PORT   = 1883
MQTT_TOPIC  = "modbus/sensor1"

#SETUP MODBUS STORE
store   = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0]*30))
context = ModbusServerContext(slaves={SLAVE_ID: store}, single=False)

identity = ModbusDeviceIdentification()
identity.VendorName        = 'IoT Demo'
identity.ProductCode       = 'DE'
identity.VendorUrl         = 'https://example.com'
identity.ProductName       = 'ModbusSim'
identity.ModelName         = 'ModbusSim'
identity.MajorMinorRevision= '1.0'

#SETUP MQTT CLIENT
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
mqtt_client.reconnect_delay_set(min_delay=1, max_delay=120)
mqtt_client.loop_start()


#HELPERS
def float_to_regs(f):
    b = struct.pack('>f', f)
    return [int.from_bytes(b[0:2], 'big'), int.from_bytes(b[2:4], 'big')]

#SERVER THREAD
def run_modbus_server():
    print("Modbus Simulator listening on port 502")
    StartTcpServer(context, identity=identity, address=("0.0.0.0", 502))

server_thread = threading.Thread(target=run_modbus_server, daemon=True)
server_thread.start()

#UPDATE LOOP 
def update_and_publish():
    idx = 0
    while True:
        # simulate measurements
        V_L1  = 220 + 10*(idx % 3)
        I_L1  =   5 +    (idx % 3)
        VA_L1 = V_L1 * I_L1
        P_L1  = 0.9 * VA_L1

        # write into Modbus registers at addresses 1,13,19,25
        context[SLAVE_ID].setValues(3,  1, float_to_regs(V_L1))
        context[SLAVE_ID].setValues(3, 13, float_to_regs(I_L1))
        context[SLAVE_ID].setValues(3, 19, float_to_regs(VA_L1))
        context[SLAVE_ID].setValues(3, 25, float_to_regs(P_L1))

        # publish the same JSON payload
        payload = {
            "device_id":"sensor1",
            "V_L1": round(V_L1,2),
            "I_L1": round(I_L1,2),
            "VA_L1": round(VA_L1,2),
            "P_L1": round(P_L1,2),
            "timestamp": int(time.time())
        }
        result = mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
        status = result[0]
        if status == 0:
            print("Published to MQTT:", payload)
        else:
            print("Failed to send message to MQTT broker:", status)


        idx += 1
        time.sleep(2)

upd_thread = threading.Thread(target=update_and_publish, daemon=True)
upd_thread.start()

#KEEP RUNNING
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping simulator…")
