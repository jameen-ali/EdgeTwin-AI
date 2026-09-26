#include "ring_buffer.h"
#include <string.h>

TelemetryRingBuffer::TelemetryRingBuffer() {
    clear();
}

void TelemetryRingBuffer::clear() {
    head_ = 0;
    tail_ = 0;
    count_ = 0;
}

bool TelemetryRingBuffer::push(const char* json_payload) {
    if (json_payload == nullptr) return false;
    
    // If full, drop the oldest element (at head_)
    if (isFull()) {
        head_ = (head_ + 1) % RING_BUFFER_CAPACITY;
        count_--;
    }

    strncpy(buffer_[tail_], json_payload, MAX_PAYLOAD_SIZE - 1);
    buffer_[tail_][MAX_PAYLOAD_SIZE - 1] = '\0'; // Ensure null-termination

    tail_ = (tail_ + 1) % RING_BUFFER_CAPACITY;
    count_++;
    return true;
}

bool TelemetryRingBuffer::peek(char* out_payload, size_t max_len) const {
    if (isEmpty() || out_payload == nullptr || max_len == 0) return false;

    strncpy(out_payload, buffer_[head_], max_len - 1);
    out_payload[max_len - 1] = '\0';
    return true;
}

void TelemetryRingBuffer::dropFront() {
    if (!isEmpty()) {
        head_ = (head_ + 1) % RING_BUFFER_CAPACITY;
        count_--;
    }
}

bool TelemetryRingBuffer::pop(char* out_payload, size_t max_len) {
    if (!peek(out_payload, max_len)) return false;
    dropFront();
    return true;
}
