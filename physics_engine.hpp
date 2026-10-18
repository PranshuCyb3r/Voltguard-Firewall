#pragma once
#include <cstdint>
#include <cstdlib>
#include <iostream>

namespace VoltGuard {

    enum class Verdict {
        ALLOW,
        DROP_VIOLATION_RPM_MAX,
        DROP_VIOLATION_SURGE_RATE,
        DROP_INVALID_RANGE
    };

    struct PhysicsLimits {
        static constexpr uint16_t MAX_SAFE_RPM = 3600;        // Rotor physical mechanical limit
        static constexpr uint16_t MIN_OPERATIONAL_RPM = 500;   // Idle operational lower bound
        static constexpr uint16_t MAX_ACCEL_RPM_PER_SEC = 400; // Rotor inertia acceleration limit
    };

    class PhysicsEngine {
    private:
        uint16_t last_known_rpm;
        uint64_t last_timestamp_ms;

    public:
        PhysicsEngine() 
            : last_known_rpm(1800), last_timestamp_ms(0) {}

        Verdict verify_rpm_command(uint16_t requested_rpm, uint64_t current_timestamp_ms) {
            // Rule 1: Absolute Physical Limits (Mechanical yield limit: 3600 RPM)
            if (requested_rpm > PhysicsLimits::MAX_SAFE_RPM) {
                return Verdict::DROP_VIOLATION_RPM_MAX;
            }

            // Rule 2: Minimum Operational Range
            if (requested_rpm > 0 && requested_rpm < PhysicsLimits::MIN_OPERATIONAL_RPM) {
                return Verdict::DROP_INVALID_RANGE;
            }

            // Rule 3: Inertia Rate-of-Change Check (Surge delta test)
            if (last_timestamp_ms > 0 && current_timestamp_ms > last_timestamp_ms) {
                uint64_t delta_sec = (current_timestamp_ms - last_timestamp_ms) / 1000;
                if (delta_sec > 0) {
                    int32_t delta_rpm = std::abs(static_cast<int32_t>(requested_rpm) - static_cast<int32_t>(last_known_rpm));
                    uint32_t max_allowed_delta = PhysicsLimits::MAX_ACCEL_RPM_PER_SEC * delta_sec;

                    if (delta_rpm > static_cast<int32_t>(max_allowed_delta)) {
                        return Verdict::DROP_VIOLATION_SURGE_RATE;
                    }
                }
            }

            // State update if physically coherent
            last_known_rpm = requested_rpm;
            last_timestamp_ms = current_timestamp_ms;
            return Verdict::ALLOW;
        }

        static const char* verdict_to_string(Verdict v) {
            switch(v) {
                case Verdict::ALLOW: return "ALLOW (Physically Coherent)";
                case Verdict::DROP_VIOLATION_RPM_MAX: return "DROP [ALERT]: Exceeds Rotor Mechanical Yield Limit!";
                case Verdict::DROP_VIOLATION_SURGE_RATE: return "DROP [ALERT]: Instantaneous Surge Rate Physically Impossible!";
                case Verdict::DROP_INVALID_RANGE: return "DROP [ALERT]: Sub-operational Stall Envelope Violation!";
                default: return "UNKNOWN";
            }
        }
    };

} // namespace VoltGuard


