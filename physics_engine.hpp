#pragma once
#include <cstdint>
#include <cmath>
#include <iostream>
#include "digital_twin.hpp"

namespace VoltGuard {

enum class Verdict : uint8_t {
    ALLOW = 0,
    DROP_VIOLATION_RPM_MAX = 1,
    DROP_VIOLATION_CAVITATION = 2,
    DROP_VIOLATION_PRESSURE_BURST = 3,
    DROP_VIOLATION_INERTIA_SLIP = 4
};

struct PhysicsEngine {
    // Physical Plant Thresholds
    static constexpr double MAX_SAFE_RPM = 3600.0;
    static constexpr double MIN_CAVITATION_RPM = 500.0;
    static constexpr double MAX_PIPE_PRESSURE_BAR = 16.0;
    static constexpr double NOMINAL_BASELINE_BAR = 7.75;
    static constexpr double MAX_ALLOWABLE_SLIP_RPM = 500.0;

    // Fluid Dynamics Constants (Water at 20°C in Schedule 40 Steel)
    static constexpr double FLUID_DENSITY_RHO = 998.2; // kg/m^3
    static constexpr double WAVE_SPEED_C = 1200.0;     // m/s acoustic velocity
    static constexpr double VELOCITY_COEFFICIENT = 0.0024; // RPM to m/s conversion

    DigitalTwin twin;
    double last_time_sec = 0.0;

    PhysicsEngine() : twin(1800.0) {}

    // Joukowsky Water Hammer Surge Equation: Delta P = rho * c * Delta v
    static double calculate_joukowsky_shock(double commanded_rpm) {
        double delta_v = std::abs(commanded_rpm - 1800.0) * VELOCITY_COEFFICIENT;
        double delta_p_pascals = FLUID_DENSITY_RHO * WAVE_SPEED_C * delta_v;
        double delta_p_bar = delta_p_pascals / 100000.0;
        return NOMINAL_BASELINE_BAR + delta_p_bar;
    }

    // Comprehensive Cyber-Physical Invariant Evaluation
    Verdict evaluate(uint16_t raw_rpm, double current_time_sec, float& out_shock, float& out_twin_rpm) {
        double commanded_rpm = static_cast<double>(raw_rpm);
        
        // 1. Compute Joukowsky Fluid Surge Pressure
        out_shock = static_cast<float>(calculate_joukowsky_shock(commanded_rpm));

        // 2. Step RK4 Digital Twin Dynamics
        double dt = (last_time_sec == 0.0) ? 0.02 : (current_time_sec - last_time_sec);
        last_time_sec = current_time_sec;
        double twin_rpm = twin.step_rk4(commanded_rpm, dt);
        out_twin_rpm = static_cast<float>(twin_rpm);

        // 3. Multi-Invariant Tripwire Verification
        // Invariant A: Mechanical Rotor Shear Limit
        if (commanded_rpm > MAX_SAFE_RPM) {
            return Verdict::DROP_VIOLATION_RPM_MAX;
        }

        // Invariant B: Cavitation Vacuum Stall Limit
        if (commanded_rpm < MIN_CAVITATION_RPM) {
            return Verdict::DROP_VIOLATION_CAVITATION;
        }

        // Invariant C: Hydrodynamic Pipe Rupture Limit
        if (out_shock > MAX_PIPE_PRESSURE_BAR) {
            return Verdict::DROP_VIOLATION_PRESSURE_BURST;
        }

        // Invariant D: Inertia Anomaly / Dynamic Slip Limit
        double slip = std::abs(commanded_rpm - twin_rpm);
        if (slip > MAX_ALLOWABLE_SLIP_RPM) {
            return Verdict::DROP_VIOLATION_INERTIA_SLIP;
        }

        return Verdict::ALLOW;
    }
};

} // namespace VoltGuard