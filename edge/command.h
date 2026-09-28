#ifndef COMMAND_H
#define COMMAND_H

#include <stddef.h>
#include "process_model.h"

enum CommandResultCode {
    CMD_OK = 0,
    CMD_ERR_MALFORMED_JSON = 1,
    CMD_ERR_INVALID_SCHEMA = 2,
    CMD_ERR_MACHINE_MISMATCH = 3,
    CMD_ERR_UNSAFE_INJECTION = 4,
    CMD_ERR_TRIP_LATCHED = 5,
    CMD_ERR_UNKNOWN_COMMAND = 6
};

struct CommandResult {
    CommandResultCode code;
    char message[128];
};

class EdgeCommandProcessor {
public:
    /**
     * Parse, validate, and execute an incoming MQTT command string.
     *
     * @param json_payload Raw JSON payload from edgetwin/v1/{machine_id}/cmd.
     * @param model Reference to the active EdgeProcessModel instance.
     * @param local_machine_id Configured MACHINE_ID of this ESP32 device.
     * @return CommandResult indicating success or structured rejection reason.
     */
    static CommandResult process(
        const char* json_payload,
        EdgeProcessModel& model,
        const char* local_machine_id
    );
};

#endif // COMMAND_H
