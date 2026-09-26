#ifndef TELEMETRY_H
#define TELEMETRY_H

#include <Arduino.h>
#include "process_model.h"

class TelemetryFormatter {
public:
    TelemetryFormatter();
    
    /**
     * Build canonical JSON string conforming to edgetwin.telemetry.v1.
     * 
     * @param state Process state containing sensor and derived variables.
     * @param buffered_count Count of messages queued in local ring buffer.
     * @param ts_iso ISO-8601 UTC timestamp string (e.g., "2026-09-26T12:00:00Z").
     * @param out_json Buffer to write resulting JSON string into.
     * @param max_len Maximum length of out_json buffer.
     * @return Number of bytes written, or 0 on error.
     */
    size_t formatPayload(
        const ProcessState& state,
        int buffered_count,
        const char* ts_iso,
        char* out_json,
        size_t max_len
    );

    uint32_t getSequence() const { return seq_; }
    void incrementSequence() { seq_++; }

private:
    uint32_t seq_;
};

#endif // TELEMETRY_H
