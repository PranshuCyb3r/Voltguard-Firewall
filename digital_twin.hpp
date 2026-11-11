#pragma once
#include <cmath>
#include <chrono>

namespace VoltGuard {

class DigitalTwin {
private:
    double current_velocity_rpm;
    double target_velocity_rpm;
    double last_timestamp_sec;
    
    // Plant Mechanical Parameters
    const double rotor_inertia_J = 0.85;   // kg*m^2
    const double damping_b = 0.05;         // Viscous damping coefficient
    const double max_torque_Nm = 220.0;    // Peak motor torque

    // Derivative: d(omega)/dt = (Torque - Damping * omega) / J
    double compute_derivative(double omega_rpm, double target_rpm) const {
        double error_rpm = target_rpm - omega_rpm;
        double torque = std::clamp(error_rpm * 2.5, -max_torque_Nm, max_torque_Nm);
        double omega_rad_s = omega_rpm * (2.0 * M_PI / 60.0);
        double d_omega_rad_s2 = (torque - damping_b * omega_rad_s) / rotor_inertia_J;
        return d_omega_rad_s2 * (60.0 / (2.0 * M_PI));
    }

public:
    DigitalTwin(double initial_rpm = 1800.0) 
        : current_velocity_rpm(initial_rpm), target_velocity_rpm(initial_rpm), last_timestamp_sec(0.0) {}

    // 4th-Order Runge-Kutta Numerical Step
    double step_rk4(double commanded_rpm, double dt_sec) {
        if (dt_sec <= 0.0001) dt_sec = 0.01;
        if (dt_sec > 0.5) dt_sec = 0.1; // Clamp anomalies

        target_velocity_rpm = commanded_rpm;

        double k1 = compute_derivative(current_velocity_rpm, target_velocity_rpm);
        double k2 = compute_derivative(current_velocity_rpm + 0.5 * dt_sec * k1, target_velocity_rpm);
        double k3 = compute_derivative(current_velocity_rpm + 0.5 * dt_sec * k2, target_velocity_rpm);
        double k4 = compute_derivative(current_velocity_rpm + dt_sec * k3, target_velocity_rpm);

        current_velocity_rpm += (dt_sec / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4);
        return current_velocity_rpm;
    }

    double get_current_rpm() const {
        return current_velocity_rpm;
    }

    void reset(double rpm = 1800.0) {
        current_velocity_rpm = rpm;
        target_velocity_rpm = rpm;
    }
};

} // namespace VoltGuard