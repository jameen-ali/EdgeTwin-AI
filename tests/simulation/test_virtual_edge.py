"""
tests/simulation/test_virtual_edge.py
"""

from unittest.mock import MagicMock, patch

import pytest

from simulation.virtual_edge import VirtualEdge


@pytest.fixture
def mock_mqtt_client():
    with patch("simulation.virtual_edge.mqtt.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        yield mock_client


def test_virtual_edge_init(mock_mqtt_client):
    ve = VirtualEdge(machine_id="CNC-1002", broker_host="127.0.0.1", broker_port=1883)
    assert ve.machine_id == "CNC-1002"
    assert ve.telemetry_topic == "edgetwin/v1/CNC-1002/telemetry"
    assert ve.status_topic == "edgetwin/v1/CNC-1002/status"
    assert ve.connected is False
    assert len(ve.buffer) == 0

    # Ensure LWT is set
    mock_mqtt_client.will_set.assert_called_once()
    args, kwargs = mock_mqtt_client.will_set.call_args
    assert args[0] == "edgetwin/v1/CNC-1002/status"
    assert kwargs["retain"] is True


def test_virtual_edge_connect_disconnect(mock_mqtt_client):
    ve = VirtualEdge(machine_id="MOT-9999")
    ve.connect()

    mock_mqtt_client.connect.assert_called_once_with("localhost", 1883, keepalive=60)
    mock_mqtt_client.loop_start.assert_called_once()

    ve._on_connect(mock_mqtt_client, None, None, 0, None)
    assert ve.connected is True

    # Should publish ONLINE status
    mock_mqtt_client.publish.assert_called_with(
        "edgetwin/v1/MOT-9999/status", payload='{"status": "ONLINE"}', qos=1, retain=True
    )

    ve.disconnect()
    mock_mqtt_client.loop_stop.assert_called_once()
    mock_mqtt_client.disconnect.assert_called_once()
    assert ve.connected is False


def test_virtual_edge_buffering_when_disconnected(mock_mqtt_client):
    ve = VirtualEdge(machine_id="MOT-1001", auto_start_machine=True)
    ve.connected = False  # Start disconnected

    for _ in range(5):
        ve.step()

    assert len(ve.buffer) == 5
    for i, payload in enumerate(ve.buffer):
        assert payload["seq"] == i
        assert payload["edge"]["buffered"] == i + 1


def test_virtual_edge_flush_on_reconnect(mock_mqtt_client):
    ve = VirtualEdge(machine_id="MOT-1001")
    ve.connected = False

    # Generate 3 messages while offline
    for _ in range(3):
        ve.step()

    assert len(ve.buffer) == 3

    # Mock successful publish for flush
    mock_msg_info = MagicMock()
    mock_msg_info.is_published.return_value = True
    mock_mqtt_client.publish.return_value = mock_msg_info

    # Simulate reconnect
    ve._on_connect(mock_mqtt_client, None, None, 0, None)

    # Buffer should be flushed
    assert len(ve.buffer) == 0
    assert ve.connected is True
