#ifndef PROCESS_MODEL_H
#define PROCESS_MODEL_H

#include <Arduino.h>
#include "sensors.h"

enum MachineState {
    STATE_STOPPED,
    STATE_STARTING,
    STATE_RUNNING,
    STATE_DEGRADING,
    STATE_TRIPPED
};

struct ProcessState {
    MachineState state;
    float air_temp_c;
    float process_temp_c;
    float rotational_speed_rpm;
    float torque_nm;
    float vibration_mm_s;
    float pressure_bar;
    float current_a;
    float voltage_v;
    float tool_wear_min;
    float operating_hours;
    
    // Edge computed diagnostics
    float delta_t_c;
    float power_va;
    const char* active_trip; // NULL if no trip, or "TRIP_OVERLOAD", etc.
};

class EdgeProcessModel {
public:
    EdgeProcessModel();
    void reset();
    void start();
    void stop();
    void triggerTrip(const char* trip_code);
    void update(const SensorReadings& sensors, float dt_seconds);
    const ProcessState& getState() const { return state_; }
    MachineState getMachineState() const { return state_.state; }
    bool isTripped() const { return state_.state == STATE_TRIPPED; }
    bool isConditionSafe() const;
    void injectScenario(const char* scenario_id);

private:
    ProcessState state_;
    unsigned long overload_start_ms_;
    bool overload_active_;
    
    float prng_normal(float mean, float stddev);
};

#endif // PROCESS_MODEL_H
