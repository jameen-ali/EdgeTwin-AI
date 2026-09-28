#include "command.h"
#include <string.h>
#include <stdio.h>
#include <ctype.h>

#if defined(__has_include)
  #if __has_include(<ArduinoJson.h>)
    #include <ArduinoJson.h>
    #define HAVE_ARDUINO_JSON 1
  #endif
#endif

// Helper: case-insensitive substring search
static const char* find_case_insensitive(const char* haystack, const char* needle) {
    if (!haystack || !needle) return nullptr;
    size_t needle_len = strlen(needle);
    if (needle_len == 0) return haystack;

    for (; *haystack; ++haystack) {
        if (tolower((unsigned char)*haystack) == tolower((unsigned char)*needle)) {
            size_t i = 1;
            for (; i < needle_len; ++i) {
                if (!haystack[i] || tolower((unsigned char)haystack[i]) != tolower((unsigned char)needle[i])) {
                    break;
                }
            }
            if (i == needle_len) {
                return haystack;
            }
        }
    }
    return nullptr;
}

// Fallback JSON key extraction for simple string values: "key":"value" or "key": "value"
static bool extract_json_string_value(const char* json, const char* key, char* out_buf, size_t out_len) {
    if (!json || !key || !out_buf || out_len == 0) return false;
    out_buf[0] = '\0';

    char search_pattern[64];
    snprintf(search_pattern, sizeof(search_pattern), "\"%s\"", key);
    const char* key_pos = strstr(json, search_pattern);
    if (!key_pos) return false;

    const char* colon = strchr(key_pos + strlen(search_pattern), ':');
    if (!colon) return false;

    const char* p = colon + 1;
    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') p++;

    if (*p != '\"') return false; // Non-string or malformed
    p++; // Skip opening quote

    size_t idx = 0;
    while (*p && *p != '\"' && idx < out_len - 1) {
        out_buf[idx++] = *p++;
    }
    out_buf[idx] = '\0';
    return (*p == '\"');
}

CommandResult EdgeCommandProcessor::process(
    const char* json_payload,
    EdgeProcessModel& model,
    const char* local_machine_id
) {
    CommandResult res;
    res.code = CMD_ERR_MALFORMED_JSON;
    res.message[0] = '\0';

    // 1. Basic null and empty check
    if (json_payload == nullptr || strlen(json_payload) == 0) {
        res.code = CMD_ERR_MALFORMED_JSON;
        snprintf(res.message, sizeof(res.message), "Empty command payload");
        return res;
    }

    // 2. Reject arbitrary code or shell injection patterns
    static const char* forbidden_keywords[] = {
        "__", "eval", "exec", "system", "os.", "os/", "subprocess", "sh ", "bash", "python", nullptr
    };
    for (int i = 0; forbidden_keywords[i] != nullptr; i++) {
        if (find_case_insensitive(json_payload, forbidden_keywords[i]) != nullptr) {
            res.code = CMD_ERR_UNSAFE_INJECTION;
            snprintf(res.message, sizeof(res.message), "Unsafe keyword '%s' detected. Arbitrary execution forbidden.", forbidden_keywords[i]);
            return res;
        }
    }

    // 3. Structural JSON sanity check (must begin with '{' and end with '}')
    const char* start = json_payload;
    while (*start && (*start == ' ' || *start == '\t' || *start == '\r' || *start == '\n')) start++;
    if (*start != '{') {
        res.code = CMD_ERR_MALFORMED_JSON;
        snprintf(res.message, sizeof(res.message), "Malformed JSON: missing opening brace '{'");
        return res;
    }

    const char* end = json_payload + strlen(json_payload) - 1;
    while (end > start && (*end == ' ' || *end == '\t' || *end == '\r' || *end == '\n')) end--;
    if (*end != '}') {
        res.code = CMD_ERR_MALFORMED_JSON;
        snprintf(res.message, sizeof(res.message), "Malformed JSON: missing closing brace '}'");
        return res;
    }

    char cmd_str[64] = "";
    char target_machine[64] = "";
    char scenario_id[64] = "";
    char trip_code[64] = "";

#if defined(HAVE_ARDUINO_JSON)
    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, json_payload);
    if (err) {
        res.code = CMD_ERR_MALFORMED_JSON;
        snprintf(res.message, sizeof(res.message), "JSON parse error: %s", err.c_str());
        return res;
    }

    const char* c = doc["command"] | doc["cmd"];
    if (c) strncpy(cmd_str, c, sizeof(cmd_str) - 1);

    const char* m = doc["machine_id"];
    if (m) strncpy(target_machine, m, sizeof(target_machine) - 1);

    const char* sc = doc["scenario_id"] | doc["parameters"]["scenario_id"];
    if (sc) strncpy(scenario_id, sc, sizeof(scenario_id) - 1);

    const char* tc = doc["trip_code"] | doc["parameters"]["trip_code"];
    if (tc) strncpy(trip_code, tc, sizeof(trip_code) - 1);
#else
    // Native fallback extractor
    if (!extract_json_string_value(json_payload, "command", cmd_str, sizeof(cmd_str))) {
        extract_json_string_value(json_payload, "cmd", cmd_str, sizeof(cmd_str));
    }
    extract_json_string_value(json_payload, "machine_id", target_machine, sizeof(target_machine));
    extract_json_string_value(json_payload, "scenario_id", scenario_id, sizeof(scenario_id));
    extract_json_string_value(json_payload, "trip_code", trip_code, sizeof(trip_code));
#endif

    // 4. Validate command field existence
    if (cmd_str[0] == '\0') {
        res.code = CMD_ERR_INVALID_SCHEMA;
        snprintf(res.message, sizeof(res.message), "Missing required 'command' or 'cmd' field");
        return res;
    }

    // 5. Target Machine Validation (if provided, must match local MACHINE_ID)
    if (target_machine[0] != '\0' && local_machine_id != nullptr) {
        if (strcmp(target_machine, local_machine_id) != 0) {
            res.code = CMD_ERR_MACHINE_MISMATCH;
            snprintf(res.message, sizeof(res.message), "Target machine '%s' does not match local device '%s'", target_machine, local_machine_id);
            return res;
        }
    }

    // 6. Command Dispatch with Safety Trip Guard
    if (strcmp(cmd_str, "STOP") == 0) {
        model.stop();
        res.code = CMD_OK;
        snprintf(res.message, sizeof(res.message), "Machine stopped successfully");
        return res;
    }

    if (strcmp(cmd_str, "START") == 0) {
        if (model.isTripped()) {
            res.code = CMD_ERR_TRIP_LATCHED;
            snprintf(res.message, sizeof(res.message), "Cannot start machine: safety trip is active and latched");
            return res;
        }
        model.start();
        res.code = CMD_OK;
        snprintf(res.message, sizeof(res.message), "Machine starting");
        return res;
    }

    if (strcmp(cmd_str, "RESET") == 0) {
        if (model.isTripped() && !model.isConditionSafe()) {
            res.code = CMD_ERR_TRIP_LATCHED;
            snprintf(res.message, sizeof(res.message), "Cannot reset machine: physical trip condition still hazardous");
            return res;
        }
        model.reset();
        res.code = CMD_OK;
        snprintf(res.message, sizeof(res.message), "Machine reset to nominal state");
        return res;
    }

    if (strcmp(cmd_str, "SCENARIO") == 0 || strcmp(cmd_str, "INJECT_FAULT") == 0) {
        const char* target_scenario = (scenario_id[0] != '\0') ? scenario_id : trip_code;
        if (target_scenario[0] == '\0') {
            res.code = CMD_ERR_INVALID_SCHEMA;
            snprintf(res.message, sizeof(res.message), "Missing 'scenario_id' or 'trip_code' parameter");
            return res;
        }

        // Validate canonical scenario ID (SCN-01 to SCN-08 or explicit trip codes)
        if (strcmp(target_scenario, "SCN-01") == 0 ||
            strcmp(target_scenario, "SCN-02") == 0 ||
            strcmp(target_scenario, "SCN-03") == 0 ||
            strcmp(target_scenario, "SCN-04") == 0 ||
            strcmp(target_scenario, "SCN-05") == 0 ||
            strcmp(target_scenario, "SCN-06") == 0 ||
            strcmp(target_scenario, "SCN-07") == 0 ||
            strcmp(target_scenario, "SCN-08") == 0 ||
            strcmp(target_scenario, "TRIP_OVERLOAD") == 0 ||
            strcmp(target_scenario, "TRIP_THERMAL") == 0 ||
            strcmp(target_scenario, "TRIP_OVERCURRENT") == 0 ||
            strcmp(target_scenario, "TRIP_VIBRATION") == 0) {
            
            model.injectScenario(target_scenario);
            res.code = CMD_OK;
            snprintf(res.message, sizeof(res.message), "Scenario '%s' injected successfully", target_scenario);
            return res;
        } else {
            res.code = CMD_ERR_UNKNOWN_COMMAND;
            snprintf(res.message, sizeof(res.message), "Unsupported scenario '%s'. Only SCN-01 through SCN-08 allowed.", target_scenario);
            return res;
        }
    }

    // Unsupported/unrecognized command
    res.code = CMD_ERR_UNKNOWN_COMMAND;
    snprintf(res.message, sizeof(res.message), "Unsupported command '%s'", cmd_str);
    return res;
}
