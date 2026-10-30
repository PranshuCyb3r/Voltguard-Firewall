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
        DROP_VIOLATION_INERTIA_ANOMALY = 4  // [Week 3] Dynamic RK4 Twin Tripwire
    };

    struct PhysicsLimits {
        static constexpr uint16_t MAX_SAFE_RPM = 3600;       // Dynamic shear ceiling
        static constexpr uint16_t MIN_OPERATIONAL_RPM = 500;  // Impeller cavitation collapse floor
        static constexpr float    MAX_SHOCK_BAR = 16.0f;      // Pipe rupture threshold
        
        static constexpr float FLUID_DENSITY = 998.2f;        // kg/m^3
        static constexpr float SPEED_OF_SOUND = 1480.0f;      // m/s
        static constexpr float RPM_TO_VELOCITY = 0.0016f;     // m/s per RPM
    };

    class PhysicsEngine {
    private:
        DigitalTwin twin_;

    public:
        PhysicsEngine(float baseline_rpm = 1800.0f) : twin_(baseline_rpm) {}

        static float calculate_joukowsky_shock(float rpm) {
            float delta_v = rpm * PhysicsLimits::RPM_TO_VELOCITY;
            float delta_p_pascals = PhysicsLimits::FLUID_DENSITY * PhysicsLimits::SPEED_OF_SOUND * delta_v;
            return delta_p_pascals / 100000.0f; // Convert Pascals to Bar
        }

        // Comprehensive Cyber-Physical Invariance Evaluation
        Verdict evaluate_with_twin(uint16_t commanded_rpm, float dt_seconds, float& out_shock_bar, float& out_estimated_rpm) {
            out_shock_bar = calculate_joukowsky_shock(static_cast<float>(commanded_rpm));

            // Rule 1: Cavitation Floor Breach (< 500 RPM)
            if (commanded_rpm < PhysicsLimits::MIN_OPERATIONAL_RPM) {
                return Verdict::DROP_INVALID_RANGE;
            }

            // Rule 2: Dynamic Shear Ceiling (> 3,600 RPM)
            if (commanded_rpm > PhysicsLimits::MAX_SAFE_RPM) {
                return Verdict::DROP_VIOLATION_RPM_MAX;
            }

            // Rule 3: Joukowsky Shock Overpressure (> 16.0 Bar)
            if (out_shock_bar > PhysicsLimits::MAX_SHOCK_BAR) {
                return Verdict::DROP_VIOLATION_SURGE_RATE;
            }

            // Rule 4 [Week 3]: Dynamic Inertia Anomaly Check
            // Detects impossible physical accelerations (e.g. 1800 -> 3400 RPM in sub-second ticks)
            if (twin_.is_inertial_violation(static_cast<float>(commanded_rpm), dt_seconds)) {
                return Verdict::DROP_VIOLATION_INERTIA_ANOMALY;
            }

            // If physically compliant, advance Digital Twin state using RK4 solver
            out_estimated_rpm = twin_.step_rk4(static_cast<float>(commanded_rpm), dt_seconds);
            return Verdict::ALLOW;
        }

        DigitalTwin& get_twin() { return twin_; }
    };
}