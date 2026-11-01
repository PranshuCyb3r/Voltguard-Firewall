#pragma once
#include <cstdint>
#include <cmath>
#include "digital_twin.hpp"

namespace VoltGuard {

    enum class Verdict : uint8_t {
        ALLOW = 1,
        DROP_VIOLATION_RPM_MAX = 0,
        DROP_VIOLATION_SURGE_RATE = 2,
        DROP_INVALID_RANGE = 3,
        DROP_VIOLATION_INERTIA_ANOMALY = 4
    };

    struct PhysicsLimits {
        static constexpr uint16_t MAX_SAFE_RPM = 3600;       // Rotor mechanical shear ceiling
        static constexpr uint16_t MIN_OPERATIONAL_RPM = 500;  // Impeller cavitation collapse floor
        static constexpr float    MAX_SHOCK_BAR = 16.0f;      // Pipe structural rupture ceiling (16 Bar)
        
        static constexpr float FLUID_DENSITY = 998.2f;        // Water density kg/m^3
        static constexpr float SPEED_OF_SOUND = 1480.0f;      // Acoustic speed m/s
        static constexpr float RPM_TO_VELOCITY = 0.0002916f;  // 1800 RPM = 7.75 Bar baseline
    };

    class PhysicsEngine {
    private:
        DigitalTwin twin_;

    public:
        PhysicsEngine(float baseline_rpm = 1800.0f) : twin_(baseline_rpm) {}

        static float calculate_joukowsky_shock(float rpm) {
            float delta_v = rpm * PhysicsLimits::RPM_TO_VELOCITY;
            float delta_p_pascals = PhysicsLimits::FLUID_DENSITY * PhysicsLimits::SPEED_OF_SOUND * delta_v;
            return delta_p_pascals / 100000.0f; // Converted to Bar
        }

        // Overload 1: For parser.cpp
        Verdict evaluate(uint16_t commanded_rpm, float& out_shock_bar) {
            out_shock_bar = calculate_joukowsky_shock(static_cast<float>(commanded_rpm));

            if (commanded_rpm < PhysicsLimits::MIN_OPERATIONAL_RPM) {
                return Verdict::DROP_INVALID_RANGE;
            }
            if (commanded_rpm > PhysicsLimits::MAX_SAFE_RPM) {
                return Verdict::DROP_VIOLATION_RPM_MAX;
            }
            if (out_shock_bar > PhysicsLimits::MAX_SHOCK_BAR) {
                return Verdict::DROP_VIOLATION_SURGE_RATE;
            }
            if (twin_.is_inertial_violation(static_cast<float>(commanded_rpm), 0.05f)) {
                return Verdict::DROP_VIOLATION_INERTIA_ANOMALY;
            }

            twin_.step_rk4(static_cast<float>(commanded_rpm), 0.05f);
            return Verdict::ALLOW;
        }

        // Overload 2: For server.cpp (with twin telemetry tracking)
        Verdict evaluate(uint16_t commanded_rpm, float dt_seconds, float& out_shock_bar, float& out_estimated_rpm) {
            Verdict v = evaluate(commanded_rpm, out_shock_bar);
            out_estimated_rpm = twin_.get_estimated_rpm();
            return v;
        }

        Verdict evaluate_with_twin(uint16_t commanded_rpm, float dt_seconds, float& out_shock_bar, float& out_estimated_rpm) {
            return evaluate(commanded_rpm, dt_seconds, out_shock_bar, out_estimated_rpm);
        }

        DigitalTwin& get_twin() { return twin_; }
    };
}