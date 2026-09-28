#include "process_model.h"
#if __has_include("config.h")
  #include "config.h"
#else
  #include "config.h.example"
#endif
#include <math.h>

EdgeProcessModel::EdgeProcessModel() {
    reset();
}

void EdgeProcessModel::reset() {
    if (state_.state == STATE_TRIPPED && !isConditionSafe()) {
        // Condition still unsafe; cannot reset
        return;
    }
    state_.state = STATE_RUNNING; // Default to RUNNING on boot
    state_.air_temp_c = 25.4f;
    state_.process_temp_c = 35.3f;
    state_.rotational_speed_rpm = 1548.0f;
    state_.torque_nm = 40.1f;
    state_.vibration_mm_s = 2.5f;
    state_.pressure_bar = 5.5f;
    state_.current_a = 12.0f;
    state_.voltage_v = 415.0f;
    state_.tool_wear_min = 50.0f;
    state_.operating_hours = 10000.0f;
    state_.delta_t_c = 9.9f;
    state_.power_va = 4980.0f;
    state_.active_trip = nullptr;

    overload_start_ms_ = 0;
    overload_active_ = false;
    digitalWrite(PIN_LED_TRIP, LOW);
}

void EdgeProcessModel::start() {
    if (state_.state == STATE_STOPPED && !isTripped()) {
        state_.state = STATE_STARTING;
        state_.active_trip = nullptr;
        digitalWrite(PIN_LED_TRIP, LOW);
    }
}

bool EdgeProcessModel::isConditionSafe() const {
    float delta_t = state_.process_temp_c - state_.air_temp_c;
    if (delta_t > 45.0f) return false;
    if (state_.current_a > 45.0f) return false;
    if (state_.vibration_mm_s > 15.0f) return false;
    return true;
}

void EdgeProcessModel::injectScenario(const char* scenario_id) {
    if (!scenario_id) return;

    if (strcmp(scenario_id, "SCN-04") == 0 || strcmp(scenario_id, "TRIP_OVERLOAD") == 0) {
        triggerTrip("TRIP_OVERLOAD");
    } else if (strcmp(scenario_id, "TRIP_THERMAL") == 0) {
        state_.process_temp_c = state_.air_temp_c + 46.0f;
        triggerTrip("TRIP_THERMAL");
    } else if (strcmp(scenario_id, "TRIP_OVERCURRENT") == 0) {
        state_.current_a = 46.0f;
        triggerTrip("TRIP_OVERCURRENT");
    } else if (strcmp(scenario_id, "TRIP_VIBRATION") == 0) {
        state_.vibration_mm_s = 16.0f;
        triggerTrip("TRIP_VIBRATION");
    } else if (strcmp(scenario_id, "SCN-02") == 0) {
        state_.state = STATE_DEGRADING;
        state_.process_temp_c += 15.0f;
    } else if (strcmp(scenario_id, "SCN-03") == 0) {
        state_.state = STATE_DEGRADING;
        state_.torque_nm = 55.0f;
    } else if (strcmp(scenario_id, "SCN-05") == 0) {
        state_.tool_wear_min = 245.0f;
    } else if (strcmp(scenario_id, "SCN-06") == 0) {
        state_.state = STATE_DEGRADING;
        state_.vibration_mm_s = 8.5f;
    } else if (strcmp(scenario_id, "SCN-01") == 0) {
        reset();
    }
}

void EdgeProcessModel::stop() {
    state_.state = STATE_STOPPED;
    state_.rotational_speed_rpm = 0.0f;
    state_.torque_nm = 0.0f;
    state_.current_a = 0.0f;
}

void EdgeProcessModel::triggerTrip(const char* trip_code) {
    state_.state = STATE_TRIPPED;
    state_.active_trip = trip_code;
    state_.rotational_speed_rpm = 0.0f;
    state_.torque_nm = 0.0f;
    state_.current_a = 0.0f;
    digitalWrite(PIN_LED_TRIP, HIGH); // Turn ON red trip LED
}

float EdgeProcessModel::prng_normal(float mean, float stddev) {
    // Simple Box-Muller transform for deterministic pseudo-random Gaussian noise
    float u1 = (float)random(1, 10000) / 10000.0f;
    float u2 = (float)random(1, 10000) / 10000.0f;
    float z0 = sqrt(-2.0f * log(u1)) * cos(2.0f * 3.14159265f * u2);
    return mean + z0 * stddev;
}

void EdgeProcessModel::update(const SensorReadings& sensors, float dt_seconds) {
    // 1. Air temperature from DHT22 (or fallback)
    state_.air_temp_c = sensors.air_temp_c;

    if (state_.state == STATE_TRIPPED || state_.state == STATE_STOPPED) {
        // Machine stopped / tripped: de-energized
        state_.rotational_speed_rpm = 0.0f;
        state_.torque_nm = 0.0f;
        state_.current_a = 0.0f;
        state_.voltage_v = 415.0f + prng_normal(0.0f, 0.5f);
        state_.vibration_mm_s = 0.1f + prng_normal(0.0f, 0.02f);
        state_.pressure_bar = 0.5f + prng_normal(0.0f, 0.05f);
        // Cools down toward ambient air temp
        state_.process_temp_c += 0.05f * (state_.air_temp_c - state_.process_temp_c);
    }
    else if (state_.state == STATE_STARTING) {
        // Ramping up speed
        state_.rotational_speed_rpm += (1548.0f / 5.0f);
        state_.current_a = 12.0f * 2.2f; // Inrush current spike (~26.4 A)
        state_.torque_nm = sensors.torque_nm * 0.8f;
        state_.voltage_v = 415.0f + prng_normal(0.0f, 2.0f);
        state_.vibration_mm_s = 1.2f + prng_normal(0.0f, 0.1f);
        state_.pressure_bar = 3.0f + prng_normal(0.0f, 0.2f);
        state_.process_temp_c += 0.5f * (state_.air_temp_c + 5.0f - state_.process_temp_c);

        if (state_.rotational_speed_rpm >= 1400.0f) {
            state_.state = STATE_RUNNING;
            state_.rotational_speed_rpm = 1548.0f;
        }
    }
    else if (state_.state == STATE_RUNNING || state_.state == STATE_DEGRADING) {
        // Mechanical torque from slide potentiometer
        state_.torque_nm = sensors.torque_nm + prng_normal(0.0f, 0.5f);
        
        // Speed follows nominal with slight load droop
        float load_droop = (state_.torque_nm - 40.1f) * 1.5f;
        state_.rotational_speed_rpm = 1548.0f - load_droop + prng_normal(0.0f, 5.0f);
        if (state_.rotational_speed_rpm < 0.0f) state_.rotational_speed_rpm = 0.0f;

        // Current coupled to torque: I = 12.0 * (torque / 40.1)
        float load_factor = state_.torque_nm / 40.1f;
        state_.current_a = 12.0f * load_factor + prng_normal(0.0f, 0.2f);
        if (state_.current_a < 0.0f) state_.current_a = 0.0f;

        // Voltage nominal
        state_.voltage_v = 415.0f + prng_normal(0.0f, 1.5f);

        // Thermal dissipation equilibrium
        float load_heat = 0.5f * pow(state_.current_a / 12.0f, 2) + 0.5f * (state_.torque_nm / 40.1f);
        float target_proc_temp = state_.air_temp_c + 9.9f + (load_heat - 1.0f) * 2.0f;
        state_.process_temp_c += 0.25f * (target_proc_temp - state_.process_temp_c);
        state_.process_temp_c += prng_normal(0.0f, 0.1f);

        // Vibration: MPU6050 reading + tool wear factor
        float wear_vib = (state_.tool_wear_min > 150.0f) ? ((state_.tool_wear_min - 150.0f) / 100.0f) * 0.8f : 0.0f;
        state_.vibration_mm_s = sensors.vibration_mm_s + wear_vib + prng_normal(0.0f, 0.1f);

        // Pressure coupled to speed and load
        state_.pressure_bar = 5.5f + (state_.rotational_speed_rpm / 1548.0f - 1.0f) * 1.5f + prng_normal(0.0f, 0.1f);

        // Tool wear and runtime accumulation
        float wear_mult = 1.0f + ((state_.torque_nm > 40.0f) ? (state_.torque_nm - 40.0f) / 30.0f : 0.0f);
        state_.tool_wear_min += 0.1f * wear_mult * dt_seconds;
        state_.operating_hours += dt_seconds / 3600.0f;

        // -------------------------------------------------------------------
        // Safety / Trip Evaluation
        // -------------------------------------------------------------------
        float current_delta_t = state_.process_temp_c - state_.air_temp_c;
        
        // 1. Sustained Overload Check (>= 32 A for >= 10 s)
        if (state_.current_a >= 32.0f) {
            if (!overload_active_) {
                overload_active_ = true;
                overload_start_ms_ = millis();
            } else if (millis() - overload_start_ms_ >= OVERLOAD_TRIP_DELAY_MS) {
                triggerTrip("TRIP_OVERLOAD");
            }
        } else {
            overload_active_ = false;
        }

        // 2. Immediate Safety Limit Trips
        if (state_.state != STATE_TRIPPED) {
            if (current_delta_t > 45.0f) {
                triggerTrip("TRIP_THERMAL");
            } else if (state_.current_a > 45.0f) {
                triggerTrip("TRIP_OVERCURRENT");
            } else if (state_.vibration_mm_s > 15.0f) {
                triggerTrip("TRIP_VIBRATION");
            }
        }
    }

    // Update edge diagnostics
    state_.delta_t_c = state_.process_temp_c - state_.air_temp_c;
    state_.power_va = state_.voltage_v * state_.current_a;
}
