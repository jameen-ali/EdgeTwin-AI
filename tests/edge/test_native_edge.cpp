#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "mock_arduino.h"
#include "../../edge/process_model.h"
#include "../../edge/ring_buffer.h"
#include "../../edge/telemetry.h"
#include "../../edge/command.h"

#define TEST_ASSERT(cond, msg) \
    do { \
        if (!(cond)) { \
            fprintf(stderr, "FAILED: %s (at line %d): %s\n", __FUNCTION__, __LINE__, msg); \
            assert(cond); \
        } \
    } while(0)

// ----------------------------------------------------------------------------
// Process Model & Safety Trip Tests
// ----------------------------------------------------------------------------

void test_process_model_nominal_boot() {
    EdgeProcessModel model;
    const ProcessState& s = model.getState();

    TEST_ASSERT(s.state == STATE_RUNNING, "Model should boot into STATE_RUNNING");
    TEST_ASSERT(s.rotational_speed_rpm > 1500.0f, "Nominal RPM should be ~1548");
    TEST_ASSERT(s.current_a > 10.0f && s.current_a < 15.0f, "Nominal current should be ~12A");
    TEST_ASSERT(s.active_trip == nullptr, "No trip on boot");
    TEST_ASSERT(get_pin_state(2) == LOW, "Trip LED should be LOW on boot");
    printf("PASS: test_process_model_nominal_boot\n");
}

void test_process_model_stop_start_transitions() {
    EdgeProcessModel model;
    model.stop();
    TEST_ASSERT(model.getMachineState() == STATE_STOPPED, "State should be STOPPED");
    TEST_ASSERT(model.getState().rotational_speed_rpm == 0.0f, "RPM should be 0 when stopped");
    TEST_ASSERT(model.getState().current_a == 0.0f, "Current should be 0 when stopped");

    model.start();
    TEST_ASSERT(model.getMachineState() == STATE_STARTING, "State should transition to STARTING");

    // Advance 1 tick in STARTING state to observe inrush current
    SensorReadings sensors = {25.4f, 40.1f, 2.5f, true, true, true};
    model.update(sensors, 1.0f);
    TEST_ASSERT(model.getState().current_a > 20.0f, "Starting inrush current should be elevated");

    // Advance remaining ticks until ramp completes
    for (int i = 0; i < 5; i++) {
        model.update(sensors, 1.0f);
    }
    TEST_ASSERT(model.getMachineState() == STATE_RUNNING, "State should ramp into RUNNING");
    printf("PASS: test_process_model_stop_start_transitions\n");
}

void test_thermal_safety_trip() {
    EdgeProcessModel model;
    set_simulated_millis(1000);

    // Provide high process temperature resulting in DeltaT > 45 C
    model.injectScenario("TRIP_THERMAL");
    SensorReadings sensors = {20.0f, 40.1f, 2.5f, true, true, true};
    model.update(sensors, 1.0f);

    TEST_ASSERT(model.isTripped(), "Machine should be in STATE_TRIPPED");
    TEST_ASSERT(strcmp(model.getState().active_trip, "TRIP_THERMAL") == 0, "Active trip should be TRIP_THERMAL");
    TEST_ASSERT(model.getState().rotational_speed_rpm == 0.0f, "RPM must be 0 after trip");
    TEST_ASSERT(model.getState().torque_nm == 0.0f, "Torque must be 0 after trip");
    TEST_ASSERT(model.getState().current_a == 0.0f, "Current must be 0 after trip");
    TEST_ASSERT(get_pin_state(2) == HIGH, "Trip LED (pin 2) must be HIGH after trip");
    printf("PASS: test_thermal_safety_trip\n");
}

void test_overcurrent_safety_trip() {
    EdgeProcessModel model;
    set_simulated_millis(2000);

    model.injectScenario("TRIP_OVERCURRENT");
    SensorReadings sensors = {25.0f, 40.1f, 2.5f, true, true, true};
    model.update(sensors, 1.0f);

    TEST_ASSERT(model.isTripped(), "Machine should trip on overcurrent");
    TEST_ASSERT(strcmp(model.getState().active_trip, "TRIP_OVERCURRENT") == 0, "Active trip should be TRIP_OVERCURRENT");
    TEST_ASSERT(model.getState().rotational_speed_rpm == 0.0f, "RPM must be 0 after trip");
    TEST_ASSERT(model.getState().current_a == 0.0f, "Current must be 0 after trip");
    TEST_ASSERT(get_pin_state(2) == HIGH, "Trip LED must be HIGH");
    printf("PASS: test_overcurrent_safety_trip\n");
}

void test_vibration_safety_trip() {
    EdgeProcessModel model;
    set_simulated_millis(3000);

    model.injectScenario("TRIP_VIBRATION");
    SensorReadings sensors = {25.0f, 40.1f, 16.5f, true, true, true};
    model.update(sensors, 1.0f);

    TEST_ASSERT(model.isTripped(), "Machine should trip on vibration > 15 mm/s");
    TEST_ASSERT(strcmp(model.getState().active_trip, "TRIP_VIBRATION") == 0, "Active trip should be TRIP_VIBRATION");
    TEST_ASSERT(model.getState().rotational_speed_rpm == 0.0f, "RPM must be 0 after trip");
    TEST_ASSERT(get_pin_state(2) == HIGH, "Trip LED must be HIGH");
    printf("PASS: test_vibration_safety_trip\n");
}

void test_sustained_overload_safety_trip() {
    EdgeProcessModel model;
    unsigned long base_ms = 10000;
    set_simulated_millis(base_ms);

    // Slide potentiometer sets heavy load causing current >= 32 A
    // (potentiometer scaled to 110 Nm -> ~33A current)
    SensorReadings heavy_load = {25.0f, 115.0f, 2.5f, true, true, true};

    // Step for 9 seconds: should not trip yet
    for (int s = 0; s < 9; s++) {
        set_simulated_millis(base_ms + s * 1000);
        model.update(heavy_load, 1.0f);
        TEST_ASSERT(!model.isTripped(), "Should not trip before 10s of sustained overload");
    }

    // Step at 10.5 seconds: sustained overload triggers trip
    set_simulated_millis(base_ms + 10500);
    model.update(heavy_load, 1.0f);
    TEST_ASSERT(model.isTripped(), "Should trip after >= 10s of sustained overload >= 32A");
    TEST_ASSERT(strcmp(model.getState().active_trip, "TRIP_OVERLOAD") == 0, "Active trip should be TRIP_OVERLOAD");
    TEST_ASSERT(model.getState().rotational_speed_rpm == 0.0f, "RPM must drop to 0");
    TEST_ASSERT(model.getState().current_a == 0.0f, "Current must drop to 0");
    TEST_ASSERT(get_pin_state(2) == HIGH, "Trip LED must be HIGH");
    printf("PASS: test_sustained_overload_safety_trip\n");
}

void test_trip_latch_and_bypass_prevention() {
    EdgeProcessModel model;
    model.injectScenario("TRIP_THERMAL");
    TEST_ASSERT(model.isTripped(), "Must be in TRIPPED state");

    // Attempting start() while tripped must be rejected
    model.start();
    TEST_ASSERT(model.isTripped(), "Start command must not bypass an active trip");
    TEST_ASSERT(model.getState().rotational_speed_rpm == 0.0f, "RPM must remain 0");

    // Attempting reset() while still thermally hazardous must be rejected
    model.getState(); // inspect
    model.reset();
    TEST_ASSERT(model.isTripped(), "Reset must not bypass an active hazard");
    printf("PASS: test_trip_latch_and_bypass_prevention\n");
}

// ----------------------------------------------------------------------------
// Ring Buffer Tests
// ----------------------------------------------------------------------------

void test_ring_buffer_bounded_fifo() {
    TelemetryRingBuffer rb;
    TEST_ASSERT(rb.isEmpty(), "Ring buffer should be empty initially");
    TEST_ASSERT(rb.size() == 0, "Initial count 0");

    char out_buf[MAX_PAYLOAD_SIZE];

    // Push 3 items
    rb.push("{\"msg\":1}");
    rb.push("{\"msg\":2}");
    rb.push("{\"msg\":3}");
    TEST_ASSERT(rb.size() == 3, "Count should be 3");

    // Pop and verify FIFO order
    rb.pop(out_buf, sizeof(out_buf));
    TEST_ASSERT(strcmp(out_buf, "{\"msg\":1}") == 0, "First popped should be msg 1");
    rb.pop(out_buf, sizeof(out_buf));
    TEST_ASSERT(strcmp(out_buf, "{\"msg\":2}") == 0, "Second popped should be msg 2");
    rb.pop(out_buf, sizeof(out_buf));
    TEST_ASSERT(strcmp(out_buf, "{\"msg\":3}") == 0, "Third popped should be msg 3");
    TEST_ASSERT(rb.isEmpty(), "Buffer should be empty after popping all");

    // Fill to capacity (50 items)
    char item_buf[64];
    for (int i = 0; i < 50; i++) {
        snprintf(item_buf, sizeof(item_buf), "{\"seq\":%d}", i);
        bool ok = rb.push(item_buf);
        TEST_ASSERT(ok, "Push must succeed");
    }
    TEST_ASSERT(rb.isFull(), "Buffer must be full at 50 items");
    TEST_ASSERT(rb.size() == 50, "Buffer size must equal capacity (50)");

    // Push 51st item: should drop oldest item (seq 0) and remain at size 50
    rb.push("{\"seq\":50}");
    TEST_ASSERT(rb.size() == 50, "Buffer size must not exceed capacity");

    // Oldest item should now be seq 1 (seq 0 was dropped)
    rb.pop(out_buf, sizeof(out_buf));
    TEST_ASSERT(strcmp(out_buf, "{\"seq\":1}") == 0, "Oldest item dropped; seq 1 expected");
    TEST_ASSERT(rb.size() == 49, "Size should be 49 after 1 pop");

    printf("PASS: test_ring_buffer_bounded_fifo\n");
}

// ----------------------------------------------------------------------------
// Telemetry Formatter Tests
// ----------------------------------------------------------------------------

void test_telemetry_formatter() {
    EdgeProcessModel model;
    TelemetryFormatter fmt;
    char json_buf[1024];

    TEST_ASSERT(fmt.getSequence() == 0, "Initial sequence should be 0");

    size_t len = fmt.formatPayload(
        model.getState(),
        0,
        "2026-09-28T12:00:00Z",
        json_buf,
        sizeof(json_buf)
    );

    TEST_ASSERT(len > 0, "Payload length must be > 0");
    TEST_ASSERT(strstr(json_buf, "\"schema\":\"edgetwin.telemetry.v1\"") != nullptr, "Must contain schema");
    TEST_ASSERT(strstr(json_buf, "\"machine_id\":\"MOT-1001\"") != nullptr, "Must contain machine_id");
    TEST_ASSERT(strstr(json_buf, "\"seq\":0") != nullptr, "Must contain sequence 0");
    TEST_ASSERT(strstr(json_buf, "\"trip\":null") != nullptr, "Nominal trip must be null");

    // Increment sequence
    fmt.incrementSequence();
    TEST_ASSERT(fmt.getSequence() == 1, "Sequence must increment to 1");

    // Format tripped state
    model.triggerTrip("TRIP_OVERLOAD");
    len = fmt.formatPayload(
        model.getState(),
        5,
        "2026-09-28T12:00:01Z",
        json_buf,
        sizeof(json_buf)
    );
    TEST_ASSERT(strstr(json_buf, "\"trip\":\"TRIP_OVERLOAD\"") != nullptr, "Must format trip code string");
    TEST_ASSERT(strstr(json_buf, "\"buffered\":5") != nullptr, "Must format buffered count");

    printf("PASS: test_telemetry_formatter\n");
}

// ----------------------------------------------------------------------------
// Command Processor Tests
// ----------------------------------------------------------------------------

void test_command_processor_stop_start() {
    EdgeProcessModel model;
    const char* machine_id = "MOT-1001";

    // Valid STOP command
    CommandResult r1 = EdgeCommandProcessor::process("{\"command\": \"STOP\"}", model, machine_id);
    TEST_ASSERT(r1.code == CMD_OK, "STOP command should succeed");
    TEST_ASSERT(model.getMachineState() == STATE_STOPPED, "Machine should be stopped");

    // Valid START command
    CommandResult r2 = EdgeCommandProcessor::process("{\"command\": \"START\"}", model, machine_id);
    TEST_ASSERT(r2.code == CMD_OK, "START command should succeed");
    TEST_ASSERT(model.getMachineState() == STATE_STARTING, "Machine should be starting");

    printf("PASS: test_command_processor_stop_start\n");
}

void test_command_processor_trip_latched_prevention() {
    EdgeProcessModel model;
    const char* machine_id = "MOT-1001";

    model.triggerTrip("TRIP_OVERLOAD");
    TEST_ASSERT(model.isTripped(), "Machine should be tripped");

    // Attempt START when tripped
    CommandResult r1 = EdgeCommandProcessor::process("{\"command\": \"START\"}", model, machine_id);
    TEST_ASSERT(r1.code == CMD_ERR_TRIP_LATCHED, "START command must be rejected when tripped");
    TEST_ASSERT(model.isTripped(), "Machine must remain tripped");

    printf("PASS: test_command_processor_trip_latched_prevention\n");
}

void test_command_processor_machine_mismatch() {
    EdgeProcessModel model;
    const char* machine_id = "MOT-1001";

    CommandResult r = EdgeCommandProcessor::process("{\"command\": \"STOP\", \"machine_id\": \"PMP-2001\"}", model, machine_id);
    TEST_ASSERT(r.code == CMD_ERR_MACHINE_MISMATCH, "Mismatched machine ID must be rejected");
    TEST_ASSERT(model.getMachineState() == STATE_RUNNING, "Command must not execute on mismatched machine");

    printf("PASS: test_command_processor_machine_mismatch\n");
}

void test_command_processor_malformed_and_injection_rejection() {
    EdgeProcessModel model;
    const char* machine_id = "MOT-1001";

    // Empty payload
    CommandResult r1 = EdgeCommandProcessor::process("", model, machine_id);
    TEST_ASSERT(r1.code == CMD_ERR_MALFORMED_JSON, "Empty payload must be rejected");

    // Malformed JSON (no closing brace)
    CommandResult r2 = EdgeCommandProcessor::process("{\"command\": \"STOP\"", model, machine_id);
    TEST_ASSERT(r2.code == CMD_ERR_MALFORMED_JSON, "Missing brace must be rejected");

    // Missing command field
    CommandResult r3 = EdgeCommandProcessor::process("{\"machine_id\": \"MOT-1001\"}", model, machine_id);
    TEST_ASSERT(r3.code == CMD_ERR_INVALID_SCHEMA, "Missing command field must be rejected");

    // Dangerous code injection
    CommandResult r4 = EdgeCommandProcessor::process("{\"command\": \"eval('import os; os.system()')\"}", model, machine_id);
    TEST_ASSERT(r4.code == CMD_ERR_UNSAFE_INJECTION, "Unsafe injection keyword must be blocked");

    // Shell keyword injection
    CommandResult r5 = EdgeCommandProcessor::process("{\"command\": \"system\", \"args\": \"reboot\"}", model, machine_id);
    TEST_ASSERT(r5.code == CMD_ERR_UNSAFE_INJECTION, "Shell injection keyword must be blocked");

    // Unknown command
    CommandResult r6 = EdgeCommandProcessor::process("{\"command\": \"UNSUPPORTED_OP\"}", model, machine_id);
    TEST_ASSERT(r6.code == CMD_ERR_UNKNOWN_COMMAND, "Unknown command must be rejected");

    printf("PASS: test_command_processor_malformed_and_injection_rejection\n");
}

int main() {
    printf("==================================================\n");
    printf("Running Native Edge C++ Firmware Unit Tests\n");
    printf("==================================================\n");

    test_process_model_nominal_boot();
    test_process_model_stop_start_transitions();
    test_thermal_safety_trip();
    test_overcurrent_safety_trip();
    test_vibration_safety_trip();
    test_sustained_overload_safety_trip();
    test_trip_latch_and_bypass_prevention();
    test_ring_buffer_bounded_fifo();
    test_telemetry_formatter();
    test_command_processor_stop_start();
    test_command_processor_trip_latched_prevention();
    test_command_processor_machine_mismatch();
    test_command_processor_malformed_and_injection_rejection();

    printf("==================================================\n");
    printf("All 13 Native Edge C++ Unit Tests PASSED!\n");
    printf("==================================================\n");
    return 0;
}
