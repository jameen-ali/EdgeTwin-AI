#include "telemetry.h"
#include "config.h"
#include <stdio.h>

TelemetryFormatter::TelemetryFormatter() : seq_(0) {}

size_t TelemetryFormatter::formatPayload(
    const ProcessState& state,
    int buffered_count,
    const char* ts_iso,
    char* out_json,
    size_t max_len
) {
    // Determine vibration quality flag
    const char* q_vib = "OK";
    if (state.vibration_mm_s > 7.0f) {
        q_vib = "LIMIT_ALARM";
    } else if (state.vibration_mm_s > 4.5f) {
        q_vib = "LIMIT_WARN";
    }

    // Determine pressure quality flag
    const char* q_press = "OK";
    if (state.pressure_bar > 8.0f) {
        q_press = "LIMIT_ALARM";
    }

    // Format trip string or null literal
    char trip_buf[32];
    if (state.active_trip != nullptr) {
        snprintf(trip_buf, sizeof(trip_buf), "\"%s\"", state.active_trip);
    } else {
        snprintf(trip_buf, sizeof(trip_buf), "null");
    }

    // Strict formatting matching edgetwin.telemetry.v1 schema
    int written = snprintf(
        out_json, max_len,
        "{"
        "\"schema\":\"%s\","
        "\"machine_id\":\"%s\","
        "\"seq\":%lu,"
        "\"ts\":\"%s\","
        "\"provenance\":\"%s\","
        "\"fw\":\"%s\","
        "\"signals\":{"
            "\"air_temp_c\":%.2f,"
            "\"process_temp_c\":%.2f,"
            "\"rotational_speed_rpm\":%.1f,"
            "\"torque_nm\":%.2f,"
            "\"vibration_mm_s\":%.2f,"
            "\"pressure_bar\":%.2f,"
            "\"current_a\":%.2f,"
            "\"voltage_v\":%.2f,"
            "\"tool_wear_min\":%.2f,"
            "\"operating_hours\":%.4f"
        "},"
        "\"quality\":{"
            "\"vibration_mm_s\":\"%s\","
            "\"pressure_bar\":\"%s\""
        "},"
        "\"edge\":{"
            "\"delta_t_c\":%.2f,"
            "\"power_va\":%.2f,"
            "\"trip\":%s,"
            "\"buffered\":%d"
        "}"
        "}",
        SCHEMA_ID,
        MACHINE_ID,
        (unsigned long)seq_,
        ts_iso,
        PROVENANCE,
        FIRMWARE_VERSION,
        state.air_temp_c,
        state.process_temp_c,
        state.rotational_speed_rpm,
        state.torque_nm,
        state.vibration_mm_s,
        state.pressure_bar,
        state.current_a,
        state.voltage_v,
        state.tool_wear_min,
        state.operating_hours,
        q_vib,
        q_press,
        state.delta_t_c,
        state.power_va,
        trip_buf,
        buffered_count
    );

    if (written < 0 || (size_t)written >= max_len) {
        return 0; // Truncation or formatting error
    }

    return (size_t)written;
}
