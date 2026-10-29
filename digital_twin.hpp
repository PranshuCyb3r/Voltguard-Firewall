#pragma once
#include <cstdint>
#include <cmath>

namespace VoltGuard {

    // Industrial Rotor & Fluid Physical Parameters
    struct TwinParameters {
        float moment_of_inertia = 0.85f;    // J (kg*m^2) - Physical rotor mass resistance
        float damping_coefficient = 0.025f;  // B (N*m*s/rad) - Bearing & fluid drag
        float motor_torque_constant = 1.25f;// Kt - Electromagnetic torque gain
        float max_safe_accel_rpm_s = 400.0f;// Maximum physical acceleration limit (RPM/sec)
    };

    class DigitalTwin {
    private:
        float current_rpm_;
        uint64_t last_timestamp_ns_;
        TwinParameters params_;

        // Rotor ODE: d(omega)/dt = (Torque - Damping*omega) / Inertia
        float derivative(float rpm, float target_rpm) const {
            float torque = params_.motor_torque_constant * (target_rpm - rpm);
            float drag = params_.damping_coefficient * rpm;
            return (torque - drag) / params_.moment_of_inertia;
        }

    public:
        DigitalTwin(float initial_rpm = 1800.0f)
            : current_rpm_(initial_rpm), last_timestamp_ns_(0) {}

        // Runge-Kutta 4th Order (RK4) Numerical ODE Solver
        // Solves physical state transition between telemetry ticks (dt in seconds)
        float step_rk4(float target_rpm, float dt) {
            if (dt <= 0.0f || dt > 1.0f) {
                dt = 0.02f; // Fallback to nominal 20ms tick
            }

            float k1 = derivative(current_rpm_, target_rpm);
            float k2 = derivative(current_rpm_ + 0.5f * dt * k1, target_rpm);
            float k3 = derivative(current_rpm_ + 0.5f * dt * k2, target_rpm);
            float k4 = derivative(current_rpm_ + dt * k3, target_rpm);

            // Weighted average RK4 formula
            current_rpm_ += (dt / 6.0f) * (k1 + 2.0f * k2 + 2.0f * k3 + k4);
            return current_rpm_;
        }

        // Check if commanded RPM violates laws of physical inertia
        bool is_inertial_violation(float commanded_rpm, float dt) const {
            if (dt <= 0.0001f) return false;
            float requested_accel = std::abs(commanded_rpm - current_rpm_) / dt;
            return requested_accel > params_.max_safe_accel_rpm_s;
        }

        float get_estimated_rpm() const { return current_rpm_; }
        void set_rpm(float rpm) { current_rpm_ = rpm; }
    };

}