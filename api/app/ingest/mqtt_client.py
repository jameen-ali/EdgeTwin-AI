"""
api/app/ingest/mqtt_client.py — Resilient MQTT ingestion client (T-032).

Wraps paho-mqtt VERSION2 into a lifecycle-managed service that:
- Connects to the configured Mosquitto broker on startup.
- Subscribes to ``edgetwin/v1/+/telemetry`` after each (re)connect.
- Dispatches messages to handle_message() using a DB session from SessionLocal.
- Handles reconnects automatically via paho's loop_start() background thread.
- Disconnects cleanly on application shutdown.

All MQTT credentials are sourced from Settings (never hardcoded).
"""

from __future__ import annotations

import logging
import ssl
import threading
from typing import Any

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session

from api.app.config import Settings, get_settings
from api.app.db.session import SessionLocal
from api.app.ingest.handler import handle_message

logger = logging.getLogger(__name__)

# Canonical wildcard subscription for all machine telemetry
TELEMETRY_TOPIC = "edgetwin/v1/+/telemetry"


class MQTTIngestionClient:
    """Resilient MQTT client that subscribes and ingests telemetry.

    Lifecycle
    ---------
    ``start()`` → connects + starts paho background loop.
    ``stop()``  → disconnects + stops paho background loop.

    Thread safety
    -------------
    ``_on_message`` runs in paho's background network thread.
    Each message gets its own short-lived SQLAlchemy session to avoid
    cross-thread session sharing.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings: Settings = settings or get_settings()
        self._client: mqtt.Client = self._build_client()
        self._connected = threading.Event()
        self._stopped = False

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Connect to the broker and start the background network loop."""
        if self._stopped:
            raise RuntimeError("MQTTIngestionClient has already been stopped; create a new one.")

        s = self._settings
        logger.info(
            "MQTT ingestion client connecting",
            extra={
                "host": s.MQTT_HOST,
                "port": s.MQTT_PORT,
                "tls": s.MQTT_TLS,
                "event": "mqtt_connecting",
            },
        )

        if s.MQTT_TLS:
            self._client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

        if s.MQTT_USERNAME:
            self._client.username_pw_set(s.MQTT_USERNAME, s.MQTT_PASSWORD)

        self._client.connect_async(
            host=s.MQTT_HOST,
            port=s.MQTT_PORT,
            keepalive=60,
        )
        self._client.loop_start()

    def stop(self) -> None:
        """Disconnect and stop the background network loop gracefully."""
        self._stopped = True
        self._connected.clear()
        try:
            self._client.disconnect()
        except Exception as exc:  # noqa: BLE001  # S110: intentional silent stop
            logger.debug("Disconnect call raised during stop (ignored): %s", exc)
        self._client.loop_stop()
        logger.info(
            "MQTT ingestion client stopped",
            extra={"event": "mqtt_stopped"},
        )

    @property
    def is_connected(self) -> bool:
        """Return True if the client is currently connected to the broker."""
        return self._connected.is_set()

    # ------------------------------------------------------------------
    # Paho callbacks
    # ------------------------------------------------------------------

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        """Called by paho when connection attempt completes."""
        rc_value = getattr(reason_code, "value", reason_code)
        if rc_value == 0:
            self._connected.set()
            logger.info(
                "MQTT ingestion client connected",
                extra={"event": "mqtt_connected"},
            )
            # Subscribe after every (re)connect to handle broker restarts
            self._subscribe(client)
        else:
            self._connected.clear()
            logger.error(
                "MQTT connection refused",
                extra={"reason_code": str(reason_code), "event": "mqtt_connect_failed"},
            )

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        """Called by paho on disconnect (expected or unexpected)."""
        self._connected.clear()
        rc_value = getattr(reason_code, "value", reason_code)
        if rc_value != 0 and not self._stopped:
            logger.warning(
                "MQTT ingestion client disconnected unexpectedly; paho will reconnect",
                extra={"reason_code": str(reason_code), "event": "mqtt_disconnected"},
            )
        else:
            logger.info(
                "MQTT ingestion client disconnected cleanly",
                extra={"event": "mqtt_disconnected_clean"},
            )

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        """Dispatch every incoming MQTT message to the handler.

        Each message gets its own Session so this callback is safe to run
        in paho's network thread without sharing session state.
        """
        db: Session = SessionLocal()
        try:
            handle_message(
                topic=msg.topic,
                raw_payload=msg.payload,
                db=db,
            )
        except Exception as exc:
            # Safety net — the callback must never raise into paho
            logger.exception(
                "Unhandled exception in MQTT on_message callback",
                extra={"topic": msg.topic, "error": str(exc), "event": "mqtt_callback_error"},
            )
        finally:
            db.close()

    def _on_subscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_codes: Any,
        properties: Any,
    ) -> None:
        """Log successful subscription."""
        logger.info(
            "MQTT subscription confirmed",
            extra={"topic": TELEMETRY_TOPIC, "mid": mid, "event": "mqtt_subscribed"},
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_client(self) -> mqtt.Client:
        """Instantiate and configure the paho MQTT client."""
        s = self._settings
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=s.MQTT_CLIENT_ID,
            clean_session=True,
        )
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.on_subscribe = self._on_subscribe
        # Enable paho auto-reconnect with configured backoff
        client.reconnect_delay_set(
            min_delay=s.MQTT_RECONNECT_MIN_DELAY,
            max_delay=s.MQTT_RECONNECT_MAX_DELAY,
        )
        return client

    def _subscribe(self, client: mqtt.Client) -> None:
        """Subscribe to the canonical telemetry wildcard topic."""
        client.subscribe(TELEMETRY_TOPIC, qos=1)
        logger.info(
            "MQTT subscription requested",
            extra={"topic": TELEMETRY_TOPIC, "event": "mqtt_subscribe_requested"},
        )
