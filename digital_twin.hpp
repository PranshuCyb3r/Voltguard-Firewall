#pragma once
#include <cstdint>
#include <cmath>

namespace VoltGuard {

class DigitalTwin {
private:
    double current_rpm = 1800.0;
    double last_time_sec = 0.0;

    // OT Substation Centrifugal Pump Physical Invariants
    static constexpr double MOTOR_TORQUE_CONSTANT = 4.2;     // N*m/A equivalent drive torque
    static constexpr double ROTOR_INERTIA_J = 0.85;          // kg*m^2 (Rotational inertia)
    static constexpr double FLUID_DRAG_COEFF = 0.0018;       // Impeller viscous damping
    static constexpr double PI_CONST = 3.14159265358979323846;

    // Differential Equation: J * d(omega)/dt = Tau_motor - B * omega^2
    double compute_derivative(double omega_rpm, double target_rpm) const {
        double omega_rad_s = omega_rpm * (2.0 * PI_CONST / 60.0);
        double target_rad_s = target_rpm * (2.0 * PI_CONST / 60.0);
        
        double drive_torque = MOTOR_TORQUE_CONSTANT * (target_rad_s - omega_rad_s);
        double drag_torque = FLUID_DRAG_COEFF * omega_rad_s * std::abs(omega_rad_s);
        
        double d_omega_rad_s2 = (drive_torque - drag_torque) / ROTOR_INERTIA_J;
        return d_omega_rad_s2 * (60.0 / (2.0 * PI_CONST)); // Convert back to RPM/sec
    }

public:
    explicit DigitalTwin(double initial_rpm = 1800.0) 
        : current_rpm(initial_rpm), last_time_sec(0.0) {}

    // 4th-Order Runge-Kutta (RK4) Numerical Integration Step
    double step(double target_rpm, double current_time_sec) {
        if (last_time_sec <= 0.0) {
            last_time_sec = current_time_sec;
            return current_rpm;
        }

        double dt = current_time_sec - last_time_sec;
        if (dt <= 0.0001) dt = 0.001; // Guard against zero/negative delta
        if (dt > 0.5) dt = 0.05;      // Clamp large network hiccups

        // RK4 Numerical Integration Stages
        double k1 = compute_derivative(current_rpm, target_rpm);
        double k2 = compute_derivative(current_rpm + 0.5 * dt * k1, target_rpm);
        double k3 = compute_derivative(current_rpm + 0.5 * dt * k2, target_rpm);
        double k4 = compute_derivative(current_rpm + dt * k3, target_rpm);

        current_rpm += (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4);
        last_time_sec = current_time_sec;

        return current_rpm;
    }

    // Backward-compatible alias if evaluate() is called anywhere
    double evaluate(double target_rpm, double current_time_sec) {
        return step(target_rpm, current_time_sec);
    }

    double get_predicted_rpm() const {
        return current_rpm;
    }

    void reset(double rpm = 1800.0) {
        current_rpm = rpm;
        last_time_sec = 0.0;
    }
};

} // namespace VoltGuard
