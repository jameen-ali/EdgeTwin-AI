#ifndef SENSORS_H
#define SENSORS_H

#include <Arduino.h>

/**
 * Struct holding raw sensor acquisitions from Wokwi virtual hardware.
 */
struct SensorReadings {
    float air_temp_c;
    float torque_nm;
    float vibration_mm_s;
    bool dht_valid;
    bool mpu_valid;
    bool pot_valid;
};

void initSensors();
SensorReadings readSensors();

#endif // SENSORS_H
