#pragma once
#include <cstdint>
#include <cmath>
#include <array>
#include <algorithm>

namespace VoltGuard {

struct StateVector {
    double timestamp_sec;
    double commanded_rpm;
    double acceleration_rpm_s;
    double fluid_pressure_bar;
    double cumulative_stress_integral;
};

class StateTracker {
private:
    static constexpr size_t WINDOW_SIZE = 16;
    std::array<StateVector, WINDOW_SIZE> history_buffer{};
    size_t head_index = 0;
    size_t count = 0;

    double last_time_sec = 0.0;
    double last_rpm = 1800.0;
    double cumulative_fatigue = 0.0;

    // OT Plant Operational Invariant Thresholds
    static constexpr double MAX_SUSTAINED_CRITICAL_RPM = 3200.0; // Continuous operation warning line
    static constexpr double FATIGUE_DECAY_RATE = 0.95;           // Cooling/relaxation factor
    static constexpr double FATIGUE_THRESHOLD = 50.0;            // Rupture fatigue trip limit
    static constexpr double MAX_ANGULAR_JERK_RPM_S2 = 2500.0;    // Rate of acceleration change

public:
    StateTracker(double initial_rpm = 1800.0) 
        : last_rpm(initial_rpm), last_time_sec(0.0), cumulative_fatigue(0.0) {}

    // Ingest new wire sample and compute state-space derivatives
    StateVector update(double commanded_rpm, double current_time_sec, double pressure_bar) {
        double dt = (last_time_sec <= 0.0) ? 0.02 : (current_time_sec - last_time_sec);
        if (dt <= 0.0001) dt = 0.001;
        if (dt > 1.0) dt = 0.1; // Clamp anomaly gaps

        // 1. Angular Acceleration (d(omega)/dt)
        double accel_rpm_s = (commanded_rpm - last_rpm) / dt;

        // 2. Cumulative Kinetic Stress Integral
        // When running above nominal baseline (1800 RPM), accumulate fatigue score
        double stress_delta = std::max(0.0, commanded_rpm - 1800.0) / 100.0;
        cumulative_fatigue = (cumulative_fatigue * FATIGUE_DECAY_RATE) + (stress_delta * dt);

        StateVector state{
            current_time_sec,
            commanded_rpm,
            accel_rpm_s,
            pressure_bar,
            cumulative_fatigue
        };

        // Push to zero-allocation circular buffer
        history_buffer[head_index] = state;
        head_index = (head_index + 1) % WINDOW_SIZE;
        if (count < WINDOW_SIZE) count++;

        last_time_sec = current_time_sec;
        last_rpm = commanded_rpm;

        return state;
    }

    // Stateful Drift & Anomaly Evaluation Checks
    bool is_fatigue_limit_breached() const {
        return cumulative_fatigue > FATIGUE_THRESHOLD;
    }

    bool is_sustained_overload() const {
        if (count < 8) return false;
        // Check if last 8 packets were all operating in elevated critical stress (>3200 RPM)
        size_t elevated_count = 0;
        for (size_t i = 0; i < count; ++i) {
            if (history_buffer[i].commanded_rpm > MAX_SUSTAINED_CRITICAL_RPM) {
                elevated_count++;
            }
        }
        return elevated_count >= 8;
    }

    double get_current_fatigue() const {
        return cumulative_fatigue;
    }

    void reset(double rpm = 1800.0) {
        last_rpm = rpm;
        last_time_sec = 0.0;
        cumulative_fatigue = 0.0;
        head_index = 0;
        count = 0;
    }
};

} // namespace VoltGuard