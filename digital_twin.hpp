#pragma once
#include <cstdint>
#include <cmath>

namespace VoltGuard {

class DigitalTwin {
private:
    float current_rpm{1800.0f};
    const float inertia{0.25f}; // Motor inertia damping factor

public:
    DigitalTwin() : current_rpm(1800.0f) {}

    uint16_t step(uint16_t target_rpm, float dt) {
        // Differential dynamic response
        float d_rpm = ((float)target_rpm - current_rpm) * (dt / (dt + inertia));
        current_rpm += d_rpm;
        return static_cast<uint16_t>(current_rpm);
    }

    uint16_t get_rpm() const {
        return static_cast<uint16_t>(current_rpm);
    }
};

} // namespace VoltGuard