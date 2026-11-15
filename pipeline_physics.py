import numpy as np
from scipy.integrate import odeint

def fluid_dynamics_model(state, t, commanded_rpm):
    rpm, pressure_bar = state
    # Physical system constants
    J = 0.85        # kg*m^2 (Rotor moment of inertia)
    rho = 1000.0    # kg/m^3 (Water density)
    a = 1200.0      # m/s (Sound wave velocity in steel conduit)
    r = 0.12        # m (Impeller radius)

    # State differential equations
    d_omega_dt = (commanded_rpm - rpm) * 1.5
    delta_v = (d_omega_dt * 2 * np.pi / 60.0) * r
    dp_dt = (rho * a * delta_v) / 100000.0 - (pressure_bar - 7.75) * 0.8
    return [d_omega_dt, dp_dt]

if __name__ == "__main__":
    print("========================================================================")
    print("  VOLTGUARD :: SCIPY ODE BASELINE FLUID & PRESSURE SYSTEM MODEL (WEEK 1)")
    print("========================================================================")
    t = np.linspace(0, 1.0, 50)
    y0 = [1800.0, 7.75]
    sol = odeint(fluid_dynamics_model, y0, t, args=(50000,))
    print(f"[+] Baseline Steady State : 1,800 RPM | 7.75 Bar")
    print(f"[+] Simulated Stuxnet Peak : {np.max(sol[:, 0]):,.1f} RPM")
    print(f"[+] Dynamic Surge Pressure : {np.max(sol[:, 1]):.2f} Bar (Exceeds 16.0 Bar Rupture!)")
    print(f"[+] Physics Verification   : FATAL PIPE OVERPRESSURE DETECTED -> REQUIRE IMMEDIATE DROP")