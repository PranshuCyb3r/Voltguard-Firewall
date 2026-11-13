#pragma once
#include <cstdint>
#include <cmath>
#include <algorithm>
#include "digital_twin.hpp"
#include "state_tracker.hpp"

namespace VoltGuard {

// Deterministic Verdict Class (OT Invariant Decision Matrix)
enum class Verdict : uint8_t {
    ALLOW = 0x00,
    DROP_VIOLATION_RPM_MAX = 0x01,
    DROP_VIOLATION_CAVITATION = 0x02,
    DROP_VIOLATION_JOUKOWSKY_SHOCK = 0x03,
    DROP_VIOLATION_INERTIA_SLIP = 0x04,
    DROP_CUMULATIVE_FATIGUE = 0x05,
    DROP_SUSTAINED_OVERLOAD = 0x06
};

// Fluid & Pipe Physics Constants for Industrial Substation
struct PhysicsLimits {
    static constexpr double NOMINAL_BASELINE_RPM = 1800.0;
    static constexpr double MAX_SAFE_RPM = 3600.0;        // Mechanical shear ceiling
    static constexpr double MIN_OPERATIONAL_RPM = 500.0;   // Cavitation vacuum floor
    static constexpr double MAX_PIPE_SHOCK_BAR = 16.0;     // Joukowsky pressure rupture ceiling
    static constexpr double MAX_INERTIA_SLIP_RPM = 500.0;  // Allowed divergence from RK4 twin
};

class PhysicsEngine {
private:
    DigitalTwin twin;
    StateTracker tracker;
    
    // Joukowsky Shock Calculation Constants: Delta P = rho * a * Delta v
    static constexpr double WATER_DENSITY_RHO = 998.0;      // kg/m^3
    static constexpr double SPEED_OF_SOUND_A = 1200.0;      // m/s in steel-reinforced pipe
    static constexpr double RPM_TO_VELOCITY_COEFF = 0.00065;// Impeller tip fluid speed ratio

public:
    PhysicsEngine() : twin(1800.0), tracker(1800.0) {}

    // Hydrodynamic Pressure Shock via Joukowsky Formulation (in Bar)
    static double calculate_joukowsky_shock(double commanded_rpm) {
        double delta_rpm = std::abs(commanded_rpm - PhysicsLimits::NOMINAL_BASELINE_RPM);
        double delta_v = delta_rpm * RPM_TO_VELOCITY_COEFF;
        double delta_p_pascals = WATER_DENSITY_RHO * SPEED_OF_SOUND_A * delta_v;
        return delta_p_pascals / 100000.0; // 1 Bar = 100,000 Pa
    }

    // Comprehensive Multi-Invariant Stateful Ingress Evaluation
    Verdict evaluate(uint16_t raw_rpm, double current_time_sec, double& out_shock_bar, double& out_twin_rpm) {
        double commanded_rpm = static_cast<double>(raw_rpm);

        // 1. Joukowsky Hydrodynamic Water Hammer Shock
        out_shock_bar = calculate_joukowsky_shock(commanded_rpm);

        // 2. RK4 Digital Twin Dynamics Step
        out_twin_rpm = twin.step(commanded_rpm, current_time_sec);

        // 3. Multi-Parameter State-Space Vector Ingestion
        StateVector state = tracker.update(commanded_rpm, current_time_sec, out_shock_bar);

        // -------------------------------------------------------------
        // INVARIANT 1: Absolute Mechanical Shear Bounds
        // -------------------------------------------------------------
        if (commanded_rpm > PhysicsLimits::MAX_SAFE_RPM) {
            return Verdict::DROP_VIOLATION_RPM_MAX;
        }

        // -------------------------------------------------------------
        // INVARIANT 2: Impeller Cavitation Vacuum Boundary
        // -------------------------------------------------------------
        if (commanded_rpm < PhysicsLimits::MIN_OPERATIONAL_RPM) {
            return Verdict::DROP_VIOLATION_CAVITATION;
        }

        // -------------------------------------------------------------
        // INVARIANT 3: Pipe Burst Joukowsky Dynamic Surge
        // -------------------------------------------------------------
        if (out_shock_bar > PhysicsLimits::MAX_PIPE_SHOCK_BAR) {
            return Verdict::DROP_VIOLATION_JOUKOWSKY_SHOCK;
        }

        // -------------------------------------------------------------
        // INVARIANT 4: Dynamic Rotor Inertia Slip (Stuxnet Step Jump)
        // -------------------------------------------------------------
        double slip = std::abs(commanded_rpm - out_twin_rpm);
        if (slip > PhysicsLimits::MAX_INERTIA_SLIP_RPM) {
            return Verdict::DROP_VIOLATION_INERTIA_SLIP;
        }

        // -------------------------------------------------------------
        // INVARIANT 5: Stateful Multi-Vector Checks (Stealth Drift Guard)
        // -------------------------------------------------------------
        if (tracker.is_sustained_overload()) {
            return Verdict::DROP_SUSTAINED_OVERLOAD;
        }

        if (tracker.is_fatigue_limit_breached()) {
            return Verdict::DROP_CUMULATIVE_FATIGUE;
        }

        // ALL PHYSICAL INVARIANTS CONSERVED -> DETERMINISTIC FORWARD
        return Verdict::ALLOW;
    }

    double get_current_fatigue() const {
        return tracker.get_current_fatigue();
    }

    void reset(double baseline_rpm = 1800.0) {
        twin.reset(baseline_rpm);
        tracker.reset(baseline_rpm);
    }
};

} // namespace VoltGuard
