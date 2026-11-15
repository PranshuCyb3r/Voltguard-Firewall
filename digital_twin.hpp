#pragma once
#include <cmath>

namespace VoltGuard {

class DigitalTwin {
private:
    double current_omega; // Shaft velocity in rad/s
    double J;             // Moment of inertia (0.85 kg*m^2)
    double b;             // Viscous drag damping coefficient (0.045 N*m*s/rad)
    double tau_max;       // Peak motor torque limit (180.0 N*m)

    // First-order ODE: J * (d_omega / dt) = tau_motor - b * omega
    double derivative(double omega, double target_omega) const {
        double tau = (target_omega - omega) * 2.5;
        if (tau > tau_max) tau = tau_max;
        if (tau < -tau_max) tau = -tau_max;
        return (tau - b * omega) / J;
    }

public:
    DigitalTwin() 
        : current_omega(1800.0 * 2.0 * 3.14159265358979323846 / 60.0),
          J(0.85),
          b(0.045),
          tau_max(180.0) {}

    // Runge-Kutta 4th Order numerical integration step
    void step(double target_rpm, double dt = 0.01) {
        double target_omega = target_rpm * 2.0 * 3.14159265358979323846 / 60.0;
        
        double k1 = derivative(current_omega, target_omega);
        double k2 = derivative(current_omega + 0.5 * dt * k1, target_omega);
        double k3 = derivative(current_omega + 0.5 * dt * k2, target_omega);
        double k4 = derivative(current_omega + dt * k3, target_omega);

        current_omega += (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4);
        if (current_omega < 0.0) current_omega = 0.0;
    }

    double get_predicted_rpm() const {
        return current_omega * 60.0 / (2.0 * 3.14159265358979323846);
    }
};

} // namespace VoltGuard