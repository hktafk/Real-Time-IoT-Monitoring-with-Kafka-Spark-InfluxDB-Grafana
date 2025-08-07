# mqtt-forwarder/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY mqtt_forwarder.py .

RUN pip install pymodbus paho-mqtt

CMD ["python", "mqtt_forwarder.py"]
