#pragma once

#include <cstdint>
#include <string>
#include <cmath>

namespace VoltGuard {

enum class Verdict {
    ALLOW,
    DROP_VIOLATION_RPM_MAX,
    DROP_VIOLATION_SURGE_RATE,
    DROP_INVALID_RANGE
};

struct PhysicsLimits {
    static constexpr uint16_t MAX_SAFE_RPM        = 3600; // Rotor yield failure threshold
    static constexpr uint16_t MIN_OPERATIONAL_RPM = 500;  // Idle operational lower bound
    static constexpr uint16_t MAX_ACCEL_RPM_S     = 400;  // Max inertia acceleration limit per sec
};

class PhysicsEngine {
private:
    uint16_t last_rpm;
    int64_t  last_timestamp_ms;
    bool     initialized;

public:
    PhysicsEngine() 
        : last_rpm(1800), last_timestamp_ms(0), initialized(false) {}

    Verdict verify_rpm_command(uint16_t requested_rpm, int64_t current_time_ms) {
        // Invariant 1: Mechanical Yield Limit (Overspeed Attack Defense)
        if (requested_rpm > PhysicsLimits::MAX_SAFE_RPM) {
            return Verdict::DROP_VIOLATION_RPM_MAX;
        }

        // Invariant 2: Operational Lower Bound
        if (requested_rpm < PhysicsLimits::MIN_OPERATIONAL_RPM) {
            return Verdict::DROP_INVALID_RANGE;
        }

        // Invariant 3: Rate of Change / Rotor Inertia Constraint (Surge Attack)
        if (initialized && current_time_ms > last_timestamp_ms) {
            double delta_t_sec = static_cast<double>(current_time_ms - last_timestamp_ms) / 1000.0;
            if (delta_t_sec > 0.0001) {
                double accel = std::abs(static_cast<double>(requested_rpm) - static_cast<double>(last_rpm)) / delta_t_sec;
                if (accel > PhysicsLimits::MAX_ACCEL_RPM_S) {
                    return Verdict::DROP_VIOLATION_SURGE_RATE;
                }
            }
        }

        // State update on valid command
        last_rpm = requested_rpm;
        last_timestamp_ms = current_time_ms;
        initialized = true;

        return Verdict::ALLOW;
    }

    static std::string verdict_to_string(Verdict v) {
        switch (v) {
            case Verdict::ALLOW:
                return "ALLOW (Physically Coherent)";
            case Verdict::DROP_VIOLATION_RPM_MAX:
                return "DROP [ALERT]: Exceeds Rotor Mechanical Yield Limit!";
            case Verdict::DROP_VIOLATION_SURGE_RATE:
                return "DROP [ALERT]: Acceleration Violates Rotor Inertia Limit!";
            case Verdict::DROP_INVALID_RANGE:
                return "DROP [ALERT]: Command Below Minimum Safe Operational Bound!";
            default:
                return "DROP [ALERT]: Unknown Anomaly Detected";
        }
    }
};

} // namespace VoltGuard