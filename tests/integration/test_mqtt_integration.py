"""
tests/integration/test_mqtt_integration.py
"""

import json
import socket
import time

import paho.mqtt.client as mqtt
import pytest

from simulation.virtual_edge import VirtualEdge


def is_broker_available(host: str = "localhost", port: int = 1883) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.integration


@pytest.fixture
def broker_check():
    if not is_broker_available():
        pytest.skip("Mosquitto broker not available on localhost:1883")


def test_virtual_edge_live_publish(broker_check):
    machine_id = "MOT-9999"
    telemetry_topic = f"edgetwin/v1/{machine_id}/telemetry"
    status_topic = f"edgetwin/v1/{machine_id}/status"

    # Setup test subscriber
    received_telemetry = []
    status_updates = []

    def on_message(client, userdata, msg):
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        if topic == telemetry_topic:
            received_telemetry.append(payload)
        elif topic == status_topic:
            status_updates.append(payload)

    sub_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test_sub")
    sub_client.on_message = on_message
    sub_client.connect("localhost", 1883, 60)
    sub_client.subscribe(telemetry_topic, qos=1)
    sub_client.subscribe(status_topic, qos=1)
    sub_client.loop_start()

    # Give subscriber time to connect
    time.sleep(0.5)

    ve = VirtualEdge(machine_id=machine_id, broker_host="localhost", broker_port=1883)
    ve.connect()

    # Wait for connection
    time.sleep(0.5)

    # Step simulation
    for _ in range(3):
        ve.step()

    time.sleep(1.0)  # Wait for publish

    ve.disconnect()
    time.sleep(0.5)

    sub_client.loop_stop()
    sub_client.disconnect()

    # Assertions
    assert len(status_updates) >= 2
    assert status_updates[0]["status"] == "ONLINE"
    assert status_updates[-1]["status"] == "OFFLINE"

    assert len(received_telemetry) == 3
    for i, msg in enumerate(received_telemetry):
        assert msg["machine_id"] == machine_id
        assert msg["seq"] == i
        assert "signals" in msg
        assert "quality" in msg
