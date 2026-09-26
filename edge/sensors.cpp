#include "sensors.h"
#include "config.h"
#include <DHTesp.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

static DHTesp dht;
static Adafruit_MPU6050 mpu;
static bool mpu_initialized = false;

void initSensors() {
    // 1. Initialize DHT22
    dht.setup(PIN_DHT, DHTesp::DHT22);

    // 2. Initialize Potentiometer ADC
    pinMode(PIN_POT, INPUT);
    analogReadResolution(12); // 0-4095

    // 3. Initialize I2C and MPU6050
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    if (mpu.begin()) {
        mpu_initialized = true;
        mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
        mpu.setGyroRange(MPU6050_RANGE_500_DEG);
        mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    } else {
        mpu_initialized = false;
        Serial.println(F("[SENSORS] Warning: MPU6050 initialization failed. Using simulated vibration model."));
    }

    // 4. Initialize Hardware Safety Trip LED
    pinMode(PIN_LED_TRIP, OUTPUT);
    digitalWrite(PIN_LED_TRIP, LOW);
}

SensorReadings readSensors() {
    SensorReadings r;
    r.dht_valid = false;
    r.mpu_valid = false;
    r.pot_valid = false;

    // Read DHT22
    float t = dht.getTemperature();
    if (!isnan(t) && t >= -40.0f && t <= 80.0f) {
        r.air_temp_c = t;
        r.dht_valid = true;
    } else {
        r.air_temp_c = 25.4f; // S07 baseline fallback
    }

    // Read Slide Potentiometer (Torque proxy: 0-4095 -> 0.0-150.0 Nm)
    int raw_adc = analogRead(PIN_POT);
    if (raw_adc >= 0 && raw_adc <= 4095) {
        r.torque_nm = (float)raw_adc * (150.0f / 4095.0f);
        r.pot_valid = true;
    } else {
        r.torque_nm = 40.1f;
    }

    // Read MPU6050 Accelerometer
    if (mpu_initialized) {
        sensors_event_t a, g, temp;
        if (mpu.getEvent(&a, &g, &temp)) {
            // Compute magnitude of dynamic acceleration: |a| - 9.81 m/s^2
            float ax = a.acceleration.x;
            float ay = a.acceleration.y;
            float az = a.acceleration.z;
            float mag = sqrt(ax * ax + ay * ay + az * az);
            float dynamic_acc = fabs(mag - 9.81f);
            
            // Map dynamic acceleration (m/s^2) to velocity proxy in mm/s RMS (scale ~2.5 mm/s baseline)
            r.vibration_mm_s = dynamic_acc * 2.5f + 1.2f;
            r.mpu_valid = true;
        } else {
            r.vibration_mm_s = 2.5f;
        }
    } else {
        r.vibration_mm_s = 2.5f;
    }

    return r;
}
