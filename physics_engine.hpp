#pragma once
#include <cstdint>
#include <chrono>
#include <cmath>

namespace VoltGuard {

enum class Verdict : uint8_t {
    ALLOW = 1,
    DROP_VIOLATION_RPM_MAX = 0,
    DROP_VIOLATION_SURGE_RATE = 2,
    DROP_INVALID_RANGE = 3
};

struct PhysicsLimits {
    static constexpr float MAX_SAFE_RPM        = 3600.0f; // Mechanical shear ceiling
    static constexpr float MIN_OPERATIONAL_RPM = 500.0f;  // Sub-idle cavitation threshold
    static constexpr float MAX_ACCEL_RPM_SEC   = 400.0f;  // Inertia surge limit
    static constexpr float WATER_DENSITY       = 998.0f;  // kg/m^3 (Water)
    static constexpr float SPEED_OF_SOUND      = 1480.0f; // m/s in steel schedule-40 pipe
};

class PhysicsEngine {
private:
    float last_verified_rpm;
    std::chrono::steady_clock::time_point last_timestamp;
    bool initialized;

public:
    PhysicsEngine() : last_verified_rpm(1800.0f), initialized(false) {
        last_timestamp = std::chrono::steady_clock::now();
    }

    float calculateJoukowskyShock(float delta_rpm) {
        // Linear velocity v = (rpm * 2 * pi * r) / 60, r = 0.15m impeller
        float delta_v = (std::abs(delta_rpm) * 2.0f * 3.14159265f * 0.15f) / 60.0f;
        // Delta P = rho * a * delta_v (Pascals -> Bar)
        float delta_p_pa = PhysicsLimits::WATER_DENSITY * PhysicsLimits::SPEED_OF_SOUND * delta_v;
        return (delta_p_pa / 100000.0f); // Convert Pa to Bar
    }

    Verdict evaluate(float candidate_rpm, float& out_shock_bar) {
        auto now = std::chrono::steady_clock::now();
        float delta_t = std::chrono::duration<float>(now - last_timestamp).count();
        if (!initialized || delta_t <= 0.0f) {
            delta_t = 0.01f;
            initialized = true;
        }

        out_shock_bar = calculateJoukowskyShock(candidate_rpm - last_verified_rpm);

        // Rule 1: Physical Mechanical Ceiling
        if (candidate_rpm > PhysicsLimits::MAX_SAFE_RPM) {
            return Verdict::DROP_VIOLATION_RPM_MAX;
        }

        // Rule 2: Sub-Idle Cavitation Floor
        if (candidate_rpm < PhysicsLimits::MIN_OPERATIONAL_RPM) {
            return Verdict::DROP_INVALID_RANGE;
        }

        // Rule 3: Shaft Dynamic Surge Acceleration
        float current_accel = std::abs(candidate_rpm - last_verified_rpm) / delta_t;
        if (current_accel > PhysicsLimits::MAX_ACCEL_RPM_SEC * 10.0f) { // Transient surge window
            return Verdict::DROP_VIOLATION_SURGE_RATE;
        }

        // State update only on approved commands
        last_verified_rpm = candidate_rpm;
        last_timestamp = now;
        return Verdict::ALLOW;
    }
};

} // namespace VoltGuard
