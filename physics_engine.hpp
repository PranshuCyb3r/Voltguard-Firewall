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
    float cumulative_fatigue{12.4f};

public:
    PhysicsEngine() : last_commanded_rpm(1800), cumulative_fatigue(12.4f) {}

    Verdict evaluate(uint16_t target_rpm, float& out_shock, uint16_t& out_twin_rpm, float& out_fatigue) {
        // 1. Digital Twin Dynamic Response (dt = 0.02s / 50Hz)
        out_twin_rpm = twin.step(target_rpm, 0.02f);

        // 2. Joukowsky Transient Shock: Delta_v = Delta_omega * r (r = 0.08m)
        float delta_rpm = std::abs((float)target_rpm - (float)last_commanded_rpm);
        float delta_v = (delta_rpm * 2.0f * 3.14159265f / 60.0f) * 0.08f;
        
        // Surge pressure conversion to Bar with acoustic damping
        float raw_surge_bar = (1000.0f * 1200.0f * delta_v) / 100000.0f;
        out_shock = 7.75f + (raw_surge_bar * 0.035f);

        // 3. Basquin Cumulative Fatigue Stress Tracking
        if (delta_rpm > 1000.0f) {
            cumulative_fatigue = std::min(100.0f, cumulative_fatigue + 8.5f);
        } else {
            cumulative_fatigue = std::max(5.0f, cumulative_fatigue - 0.2f);
        }
        out_fatigue = cumulative_fatigue;

        last_commanded_rpm = target_rpm;

        // INVARIANT 1: Catastrophic Rotor Mechanical Ceiling (> 3,600 RPM)
        if (target_rpm > 3600) {
            return Verdict::DROP_VIOLATION_RPM_MAX;
        }

        // INVARIANT 2: Impeller Cavitation Vacuum Floor (< 500 RPM)
        if (target_rpm < 500) {
            return Verdict::DROP_INVALID_RANGE;
        }

        // INVARIANT 3: Pipe Burst Acoustic Rupture Ceiling (> 16.00 Bar)
        if (out_shock > 16.00f) {
            return Verdict::DROP_VIOLATION_SURGE_RATE;
        }

        // INVARIANT 4: Fatigue Endurance Limit (> 85.0 Pts)
        if (cumulative_fatigue > 85.0f) {
            return Verdict::DROP_FATIGUE_EXCEEDED;
        }

        return Verdict::ALLOW;
    }
};

} // namespace VoltGuard