#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>
#include <MQTT.h>
#include <time.h>

#if __has_include("config.h")
  #include "config.h"
#else
  #include "config.h.example"
#endif

#include "sensors.h"
#include "process_model.h"
#include "telemetry.h"
#include "ring_buffer.h"
#include "command.h"

// Networking objects
static WiFiClient netClient;
static WiFiClientSecure secureNetClient;
static MQTTClient mqttClient(1024); // Buffer size 1024 bytes (exceeds telemetry payload)

// Domain components
static EdgeProcessModel processModel;
static TelemetryFormatter formatter;
static TelemetryRingBuffer ringBuffer;

// MQTT canonical topics
static char topicTelemetry[64];
static char topicStatus[64];
static char topicCmd[64];

// Timing state
static unsigned long lastTickMs = 0;
static unsigned long bootEpochSec = 1774579200; // Deterministic base epoch (2026-03-26T00:00:00Z)
static bool sntpSynced = false;

void getIsoTimestamp(char* out_ts, size_t max_len) {
    time_t now;
    time(&now);
    struct tm timeinfo;
    if (now > 1000000000 && gmtime_r(&now, &timeinfo) != nullptr) {
        strftime(out_ts, max_len, "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
        sntpSynced = true;
    } else {
        // Deterministic fallback timestamp using internal millis offset
        unsigned long elapsedSec = millis() / 1000;
        time_t syntheticNow = (time_t)(bootEpochSec + elapsedSec);
        gmtime_r(&syntheticNow, &timeinfo);
        strftime(out_ts, max_len, "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    }
}

void onMessageReceived(String &topic, String &payload) {
    Serial.print(F("[MQTT] Command received on topic ["));
    Serial.print(topic);
    Serial.print(F("]: "));
    Serial.println(payload);

    CommandResult res = EdgeCommandProcessor::process(
        payload.c_str(),
        processModel,
        MACHINE_ID
    );

    if (res.code == CMD_OK) {
        Serial.print(F("[COMMAND] Success: "));
        Serial.println(res.message);
    } else {
        Serial.print(F("[COMMAND] Rejected (code "));
        Serial.print((int)res.code);
        Serial.print(F("): "));
        Serial.println(res.message);
    }
}

void flushBufferedTelemetry() {
    char bufferedMsg[MAX_PAYLOAD_SIZE];
    int flushCount = 0;
    const int MAX_FLUSH_PER_TICK = 10; // Bounded flush to protect safety loop execution
    while (!ringBuffer.isEmpty() && mqttClient.connected() && flushCount < MAX_FLUSH_PER_TICK) {
        if (ringBuffer.peek(bufferedMsg, sizeof(bufferedMsg))) {
            if (mqttClient.publish(topicTelemetry, bufferedMsg, false, 1)) {
                ringBuffer.dropFront();
                flushCount++;
            } else {
                break; // Publish failed, retry next cycle
            }
        } else {
            break;
        }
    }
}

void connectWiFi() {
    Serial.print(F("[WIFI] Connecting to SSID: "));
    Serial.println(WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD, WIFI_CHANNEL);

    unsigned long startMs = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startMs < 10000) {
        delay(200);
        Serial.print(F("."));
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println(F("\n[WIFI] Connected. IP: "));
        Serial.println(WiFi.localIP());
        
        // Initialize SNTP time sync
        configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    } else {
        Serial.println(F("\n[WIFI] Connection timeout. Operating in offline/buffered mode."));
    }
}

void connectMQTT() {
    if (WiFi.status() != WL_CONNECTED) {
        return;
    }

    Serial.print(F("[MQTT] Connecting to broker: "));
    Serial.print(MQTT_HOST);
    Serial.print(F(":"));
    Serial.println(MQTT_PORT);

    // Configure LWT on canonical status topic (QoS 1, Retained)
    mqttClient.setWill(topicStatus, "{\"status\":\"OFFLINE\"}", true, 1);

    // Attempt connection
    bool success = false;
    if (strlen(MQTT_USER) > 0) {
        success = mqttClient.connect(MACHINE_ID, MQTT_USER, MQTT_PASS);
    } else {
        success = mqttClient.connect(MACHINE_ID);
    }

    if (success) {
        Serial.println(F("[MQTT] Connected successfully."));

        // 1. Publish retained ONLINE status
        mqttClient.publish(topicStatus, "{\"status\":\"ONLINE\"}", true, 1);

        // 2. Subscribe to remote command topic
        mqttClient.subscribe(topicCmd, 1);

        // 3. Flush buffered telemetry
        flushBufferedTelemetry();
    } else {
        Serial.print(F("[MQTT] Connection failed. Last error: "));
        Serial.println(mqttClient.lastError());
    }
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println(F("=================================================="));
    Serial.println(F("EdgeTwin AI — ESP32 Firmware v1 (Wokwi Simulation)"));
    Serial.println(F("=================================================="));

    // Formulate canonical MQTT topics
    snprintf(topicTelemetry, sizeof(topicTelemetry), "edgetwin/v1/%s/telemetry", MACHINE_ID);
    snprintf(topicStatus, sizeof(topicStatus), "edgetwin/v1/%s/status", MACHINE_ID);
    snprintf(topicCmd, sizeof(topicCmd), "edgetwin/v1/%s/cmd", MACHINE_ID);

    // Initialize physical/virtual peripherals
    initSensors();
    processModel.reset();

    // Connect Network
    connectWiFi();

    // Initialize MQTT Client
    if (MQTT_USE_TLS) {
        secureNetClient.setInsecure(); // Test mode for Wokwi public cloud broker
        mqttClient.begin(MQTT_HOST, MQTT_PORT, secureNetClient);
    } else {
        mqttClient.begin(MQTT_HOST, MQTT_PORT, netClient);
    }
    
    mqttClient.onMessage(onMessageReceived);
    mqttClient.setOptions(60, true, 1000); // 60s keepalive, cleanSession, 1000ms timeout
    
    connectMQTT();
    lastTickMs = millis();
}

void loop() {
    // Process background MQTT packets
    mqttClient.loop();

    // Periodic telemetry loop (1 Hz non-blocking)
    unsigned long currentMs = millis();
    if (currentMs - lastTickMs >= TELEMETRY_INTERVAL_MS) {
        float dt = (currentMs - lastTickMs) / 1000.0f;
        lastTickMs = currentMs;

        // 1. Acquire sensor readings from Wokwi parts
        SensorReadings sensors = readSensors();

        // 2. Step the physical process model and evaluate safety trips
        processModel.update(sensors, dt);

        // 3. Obtain ISO-8601 UTC timestamp
        char tsIso[32];
        getIsoTimestamp(tsIso, sizeof(tsIso));

        // 4. Serialize telemetry payload according to edgetwin.telemetry.v1
        char payloadBuf[MAX_PAYLOAD_SIZE];
        size_t len = formatter.formatPayload(
            processModel.getState(),
            ringBuffer.size(),
            tsIso,
            payloadBuf,
            sizeof(payloadBuf)
        );

        if (len > 0) {
            // Increment sequence counter
            formatter.incrementSequence();

            // 5. Publish or Buffer
            if (mqttClient.connected()) {
                // Flush backlog first
                flushBufferedTelemetry();

                // Publish real-time message (QoS 1)
                bool pubOk = mqttClient.publish(topicTelemetry, payloadBuf, false, 1);
                if (!pubOk) {
                    Serial.println(F("[MQTT] Publish failed. Queuing in ring buffer."));
                    ringBuffer.push(payloadBuf);
                } else {
                    Serial.print(F("[TELEMETRY] Published seq="));
                    Serial.print(formatter.getSequence() - 1);
                    Serial.print(F(" len="));
                    Serial.println(len);
                }
            } else {
                // Offline: Queue in bounded ring buffer
                ringBuffer.push(payloadBuf);
                Serial.print(F("[BUFFER] Disconnected. Queued msg (count="));
                Serial.print(ringBuffer.size());
                Serial.println(F(")"));

                // Periodic reconnect attempt
                static unsigned long lastReconnectMs = 0;
                if (currentMs - lastReconnectMs >= 5000) {
                    lastReconnectMs = currentMs;
                    connectMQTT();
                }
            }
        }
    }
}
