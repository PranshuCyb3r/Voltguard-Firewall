#pragma once
#include <cstdint>
#include <cmath>
#include <algorithm>
#include "digital_twin.hpp"

namespace VoltGuard {

enum class Verdict : uint8_t {
    ALLOW = 0,
    DROP_VIOLATION_RPM_MAX = 1,
    DROP_VIOLATION_SURGE_RATE = 2,
    DROP_INVALID_RANGE = 4,
    DROP_FATIGUE_EXCEEDED = 5
};

class PhysicsEngine {
private:
    DigitalTwin twin;
    uint16_t last_commanded_rpm{1800};

public:
    PhysicsEngine() : last_commanded_rpm(1800) {}

    Verdict evaluate(uint16_t target_rpm, float dt, float& out_shock, uint16_t& out_twin_rpm) {
        // 1. Digital Twin Step Integration
        out_twin_rpm = twin.step(target_rpm, dt);

        // 2. Joukowsky Transient Shock: Delta_v = Delta_omega * r
        float delta_rpm = std::abs((float)target_rpm - (float)last_commanded_rpm);
        float delta_v = (delta_rpm * 2.0f * 3.14159265f / 60.0f) * 0.08f;
        
        // Scaled Joukowsky Acoustic Wave (Pascals to Bar with physical damping)
        float raw_surge_bar = (1000.0f * 1200.0f * delta_v) / 100000.0f;
        out_shock = 7.75f + (raw_surge_bar * 0.035f);

        // Update state tracking
        last_commanded_rpm = target_rpm;

        // INVARIANT 1: Catastrophic Rotor Mechanical Ceiling (> 3,600 RPM)
        if (target_rpm > 3600) {
            return Verdict::DROP_VIOLATION_RPM_MAX; // Stuxnet-class drop
        }

        // INVARIANT 2: Impeller Cavitation Vapor Floor (< 500 RPM)
        if (target_rpm < 500) {
            return Verdict::DROP_INVALID_RANGE; // Cavitation drop
        }

        // INVARIANT 3: Pipe Burst Dynamic Rupture Ceiling (> 16.00 Bar)
        if (out_shock > 16.00f) {
            return Verdict::DROP_VIOLATION_SURGE_RATE; // Water hammer drop
        }

        return Verdict::ALLOW; // Nominal & Safe Transitions Allowed
    }
};

} // namespace VoltGuard