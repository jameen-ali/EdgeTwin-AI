#ifndef RING_BUFFER_H
#define RING_BUFFER_H

#include <Arduino.h>
#if __has_include("config.h")
  #include "config.h"
#else
  #include "config.h.example"
#endif

#define MAX_PAYLOAD_SIZE 600

class TelemetryRingBuffer {
public:
    TelemetryRingBuffer();
    
    bool push(const char* json_payload);
    bool pop(char* out_payload, size_t max_len);
    bool peek(char* out_payload, size_t max_len) const;
    void dropFront();
    
    int size() const { return count_; }
    bool isEmpty() const { return count_ == 0; }
    bool isFull() const { return count_ >= RING_BUFFER_CAPACITY; }
    void clear();

private:
    char buffer_[RING_BUFFER_CAPACITY][MAX_PAYLOAD_SIZE];
    int head_;
    int tail_;
    int count_;
};

#endif // RING_BUFFER_H
