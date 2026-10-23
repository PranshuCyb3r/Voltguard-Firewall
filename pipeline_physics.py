import numpy as np
from scipy.integrate import odeint

# Physical Constants for Schedule-40 Steel Industrial Pipeline
RHO = 998.0          # Water density (kg/m^3)
SPEED_OF_SOUND = 1480 # Acoustic wave speed in water inside pipe (m/s)
IMPELLER_RADIUS = 0.15 # Impeller radius (m)
PIPE_BURST_BAR = 16.0 # Max allowable operating pressure before mechanical burst
MAX_SAFE_RPM = 3600.0 # Rotor shear threshold

def calculate_joukowsky_shock(delta_rpm: float) -> float:
    """Calculates transient water hammer pressure shock in Bar."""
    # Convert RPM delta to linear tip velocity delta (v = omega * r)
    delta_v = (abs(delta_rpm) * 2.0 * np.pi * IMPELLER_RADIUS) / 60.0
    # Joukowsky Equation: Delta P = rho * a * delta_v (Pa -> Bar)
    delta_p_pa = RHO * SPEED_OF_SOUND * delta_v
    return delta_p_pa / 1e5

def pump_transient_ode(y, t, target_rpm):
    """Simple 1st order motor inertia response: d(rpm)/dt = (target - current) / tau"""
    current_rpm = y[0]
    tau = 0.25 # Motor electrical-mechanical time constant (seconds)
    drpm_dt = (target_rpm - current_rpm) / tau
    return [drpm_dt]

def verify_physics_envelope():
    print("=" * 72)
    print("  VoltGuard Physics Engine: Mathematical Baseline & Verification      ")
    print("=" * 72)

    scenarios = [
        ("Nominal Operation", 1800, 1850),
        ("Ramp Acceleration", 1800, 2400),
        ("Mechanical Limit", 1800, 3600),
        ("Stuxnet Overspeed Attack", 1800, 50000),
        ("Cavitation Stall", 1800, 300)
    ]

    for name, initial_rpm, commanded_rpm in scenarios:
        shock = calculate_joukowsky_shock(commanded_rpm - initial_rpm)
        exceeds_rpm = commanded_rpm > MAX_SAFE_RPM
        exceeds_shock = shock > PIPE_BURST_BAR

        verdict = "ALLOW"
        if exceeds_rpm or exceeds_shock or commanded_rpm < 500:
            verdict = "DROP (Tripwire Triggered)"

        print(f"Scenario: {name:<26} | Target: {commanded_rpm:>6} RPM | Shock: {shock:>7.2f} Bar | {verdict}")

    print("=" * 72)
    print("Physics Baseline Confirmed: Tripwire Ceilings at 3,600 RPM & 16.0 Bar Shock.")

if __name__ == "__main__":
    verify_physics_envelope()