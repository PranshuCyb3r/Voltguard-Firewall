#pragma once
#include <cstdint>
#include <cmath>

namespace VoltGuard {

    enum class Verdict : uint8_t {
        ALLOW = 1,
        DROP_VIOLATION_RPM_MAX = 0,
        DROP_VIOLATION_SURGE_RATE = 2,
        DROP_INVALID_RANGE = 3
    };

    struct PhysicsLimits {
        static constexpr uint16_t MAX_SAFE_RPM = 3600;      // Dynamic mechanical shear ceiling
        static constexpr uint16_t MIN_OPERATIONAL_RPM = 500; // Impeller cavitation collapse floor
        static constexpr float    MAX_SHOCK_BAR = 16.0f;     // Joukowsky pipe burst limit (16 Bar)
        
        // Joukowsky Physical Constants
        static constexpr float FLUID_DENSITY = 998.2f;       // kg/m^3 (Water/Chamber fluid)
        static constexpr float SPEED_OF_SOUND = 1480.0f;     // m/s (Chamber acoustic velocity)
        static constexpr float RPM_TO_VELOCITY = 0.0016f;    // Geometric flow scalar (m/s per RPM)
    };

    class PhysicsEngine {
    public:
        // Joukowsky Equation: Delta P = rho * a * Delta v
        static float calculate_joukowsky_shock(float rpm) {
            float delta_v = rpm * PhysicsLimits::RPM_TO_VELOCITY;
            float delta_p_pascals = PhysicsLimits::FLUID_DENSITY * PhysicsLimits::SPEED_OF_SOUND * delta_v;
            return delta_p_pascals / 100000.0f; // Convert Pascals to Bar
        }

        // Deterministic Physics Verification Evaluation
        static Verdict evaluate(uint16_t commanded_rpm, float& out_shock_bar) {
            out_shock_bar = calculate_joukowsky_shock(static_cast<float>(commanded_rpm));

            // MidProject Review Audit 1: Impossible Physics Check (Sub-Idle Cavitation Floor < 500 RPM)
            if (commanded_rpm < PhysicsLimits::MIN_OPERATIONAL_RPM) {
                return Verdict::DROP_INVALID_RANGE;
            }

            // MidProject Review Audit 2: Mechanical Dynamic Shear Ceiling (> 3,600 RPM)
            if (commanded_rpm > PhysicsLimits::MAX_SAFE_RPM) {
                return Verdict::DROP_VIOLATION_RPM_MAX;
            }

            // Transient Water-Hammer Rupture Check (> 16.0 Bar)
            if (out_shock_bar > PhysicsLimits::MAX_SHOCK_BAR) {
                return Verdict::DROP_VIOLATION_SURGE_RATE;
            }

            return Verdict::ALLOW;
        }
    };
}