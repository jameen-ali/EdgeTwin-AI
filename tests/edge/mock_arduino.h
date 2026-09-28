#ifndef MOCK_ARDUINO_H
#define MOCK_ARDUINO_H

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1

inline unsigned long g_simulated_millis = 0;
inline int g_pin_states[64] = {0};

inline unsigned long millis() {
    return g_simulated_millis;
}

inline void set_simulated_millis(unsigned long ms) {
    g_simulated_millis = ms;
}

inline void advance_simulated_millis(unsigned long ms) {
    g_simulated_millis += ms;
}

inline void digitalWrite(uint8_t pin, uint8_t val) {
    if (pin < 64) {
        g_pin_states[pin] = val;
    }
}

inline int get_pin_state(uint8_t pin) {
    return (pin < 64) ? g_pin_states[pin] : 0;
}

inline void pinMode(uint8_t pin, uint8_t mode) {
    (void)pin;
    (void)mode;
}

inline void analogReadResolution(int bits) {
    (void)bits;
}

inline int analogRead(uint8_t pin) {
    (void)pin;
    return 1092; // 40.0 Nm nominal proxy
}

inline long random(long min_val, long max_val) {
    if (max_val <= min_val) return min_val;
    return min_val + (rand() % (max_val - min_val));
}

#endif // MOCK_ARDUINO_H
