#pragma once
#include <cstdint>
#include <cmath>
#include <algorithm>
#include "digital_twin.hpp"
#include "state_tracker.hpp"

namespace VoltGuard {

enum class Verdict : uint8_t {
    ALLOW = 0,
    DROP_VIOLATION_RPM_MAX = 1,
    DROP_VIOLATION_SURGE_RATE = 2,
    DROP_VIOLATION_FATIGUE = 3,
    DROP_VIOLATION_CAVITATION = 4
};

struct PhysicsLimits {
    static constexpr uint16_t MAX_SAFE_RPM        = 3600;   // Mechanical rotor shear tripwire
    static constexpr uint16_t MIN_OPERATIONAL_RPM = 500;    // Impeller cavitation collapse floor
    static constexpr float    MAX_JOUKOWSKY_BAR   = 16.0f;  // Pipeline rupture threshold
    static constexpr float    FLUID_DENSITY       = 1000.0f;// Treated industrial water (kg/m^3)
    static constexpr float    SPEED_OF_SOUND      = 1200.0f;// Acoustic wave speed in steel pipe (m/s)
    static constexpr double   MAX_SLEW_RATE_RPM_S = 140.0;  // Maximum torque shaft slew rate
};

class PhysicsEngine {
private:
    DigitalTwin digital_twin;
    StateTracker state_tracker;
    uint16_t last_rpm;

public:
    PhysicsEngine() : last_rpm(1800) {}

    Verdict evaluate(uint16_t commanded_rpm, float& out_shock_bar, uint16_t& out_twin_rpm, float& out_fatigue) {
        // 1. Mechanical Rotor Shear Ceiling
        if (commanded_rpm > PhysicsLimits::MAX_SAFE_RPM) {
            out_shock_bar = 48.20f;
            digital_twin.step(commanded_rpm, 0.01);
            out_twin_rpm = static_cast<uint16_t>(digital_twin.get_predicted_rpm());
            state_tracker.record_cycle(out_shock_bar, commanded_rpm);
            out_fatigue = state_tracker.get_fatigue_score();
            return Verdict::DROP_VIOLATION_RPM_MAX;
        }

        // 2. Impeller Cavitation Vacuum Collapse Floor
        if (commanded_rpm < PhysicsLimits::MIN_OPERATIONAL_RPM) {
            out_shock_bar = -1.80f;
            digital_twin.step(commanded_rpm, 0.01);
            out_twin_rpm = static_cast<uint16_t>(digital_twin.get_predicted_rpm());
            state_tracker.record_cycle(0.0f, commanded_rpm);
            out_fatigue = state_tracker.get_fatigue_score();
            return Verdict::DROP_VIOLATION_CAVITATION;
        }

        // 3. Dynamic Joukowsky Water Hammer Surge: Delta_P = rho * a * Delta_v
        double delta_rpm = std::abs(static_cast<int>(commanded_rpm) - static_cast<int>(last_rpm));
        double delta_v = (delta_rpm * 2.0 * 3.14159265358979323846 / 60.0) * 0.12; // 12cm impeller radius
        double delta_p_pa = PhysicsLimits::FLUID_DENSITY * PhysicsLimits::SPEED_OF_SOUND * delta_v;
        out_shock_bar = 7.75f + static_cast<float>(delta_p_pa / 100000.0);

        // 4. Update Digital Twin (RK4 Continuous Simulation)
        digital_twin.step(commanded_rpm, 0.01);
        out_twin_rpm = static_cast<uint16_t>(digital_twin.get_predicted_rpm());

        // 5. Update S-N Cumulative Fatigue
        state_tracker.record_cycle(out_shock_bar, commanded_rpm);
        out_fatigue = state_tracker.get_fatigue_score();

        // 6. Check Surge Overpressure Rupture Bound
        if (out_shock_bar > PhysicsLimits::MAX_JOUKOWSKY_BAR) {
            return Verdict::DROP_VIOLATION_SURGE_RATE;
        }

        // 7. Check Cumulative Fatigue Invariant
        if (state_tracker.is_fatigue_limit_exceeded()) {
            return Verdict::DROP_VIOLATION_FATIGUE;
        }

        // Valid physical invariants met
        last_rpm = commanded_rpm;
        return Verdict::ALLOW;
    }
};

} // namespace VoltGuard