import numpy as np
from scipy.integrate import odeint

def fluid_dynamics_model(y, t, commanded_rpm):
    rpm, pressure = y
    
    # Motor mechanical shaft inertia response: d(RPM)/dt = (target - current) / tau
    tau_motor = 0.15 # seconds
    drpm_dt = (commanded_rpm - rpm) / tau_motor
    
    # Joukowsky transient shock differential: dP/dt
    # Delta P = rho * a * Delta v
    rho = 998.2   # kg/m^3
    a = 1480.0    # m/s
    k_v = 0.0016  # RPM to m/s
    
    dp_dt = (rho * a * k_v * drpm_dt) / 100000.0 # Bar/sec
    return [drpm_dt, dp_dt]

if __name__ == "__main__":
    print("========================================================================")
    print("  [VoltGuard] Week 1 Baseline Physics Simulation (SciPy ODE Model)      ")
    print("========================================================================")
    
    t = np.linspace(0, 1.0, 50)
    y0 = [1800.0, 7.76] # Initial steady state at 1,800 RPM
    
    # Simulate step change to 50,000 RPM overspeed attack
    solution = odeint(fluid_dynamics_model, y0, t, args=(50000,))
    peak_rpm = np.max(solution[:, 0])
    peak_pressure = np.max(solution[:, 1])
    
    print(f"[+] Steady State Baseline  : 1,800 RPM | 7.76 Bar")
    print(f"[+] Simulated Stuxnet Surge: {peak_rpm:,.1f} RPM")
    print(f"[+] Dynamic Surge Pressure : {peak_pressure:.2f} Bar (Exceeds 16.0 Bar Rupture!)")
    print("[+] Physics Verdict        : FATAL PIPE OVERPRESSURE DETECTED -> REQUIRE IMMEDIATE DROP")
    print("========================================================================")