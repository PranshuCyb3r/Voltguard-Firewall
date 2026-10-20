import numpy as np

class PipelinePhysics:
    def __init__(self):
        self.RHO = 998.2          # Fluid density of water (kg/m^3)
        self.C_WAVE = 1200.0      # Acoustic wave propagation speed (m/s)
        self.IMPELLER_RADIUS = 0.18 # 180mm impeller
        
        # Operational Limits
        self.NOMINAL_PRESSURE_BAR = 4.5    # Normal running baseline (4.5 Bar)
        self.BURST_PRESSURE_BAR = 16.0     # Pipe catastrophic burst threshold (16 Bar)
        self.MAX_SAFE_RPM = 3600           # Mechanical yield limit
        self.MIN_SAFE_RPM = 500            # Cavitation lower bound

    def rpm_to_velocity(self, rpm: float) -> float:
        """Converts centrifugal pump RPM to fluid discharge velocity (m/s)."""
        omega = (2.0 * np.pi * rpm) / 60.0
        tangential_speed = omega * self.IMPELLER_RADIUS
        return tangential_speed * 0.35  # Slip factor

    def evaluate_setpoint(self, current_rpm: float, target_rpm: float):
        """Calculates transient surge via Joukowsky Equation: Delta_P = rho * c * Delta_v"""
        v_current = self.rpm_to_velocity(current_rpm)
        v_target = self.rpm_to_velocity(target_rpm)
        delta_v = v_target - v_current

        # Dynamic head pressure
        dynamic_head_bar = (0.5 * self.RHO * (v_target ** 2)) / 1e5
        steady_state_p = self.NOMINAL_PRESSURE_BAR + dynamic_head_bar

        # Water hammer transient shock (if sudden transition)
        surge_bar = (self.RHO * self.C_WAVE * abs(delta_v)) / 1e5 if delta_v > 0 else 0.0
        total_peak_p = steady_state_p + surge_bar

        is_burst = total_peak_p >= self.BURST_PRESSURE_BAR
        is_safe = (self.MIN_SAFE_RPM <= target_rpm <= self.MAX_SAFE_RPM) and not is_burst

        return {
            "target_rpm": target_rpm,
            "velocity_m_s": round(float(v_target), 2),
            "peak_pressure_bar": round(float(total_peak_p), 2),
            "burst_limit_bar": self.BURST_PRESSURE_BAR,
            "verdict": "ALLOW" if is_safe else ("DROP [PIPE BURST RISK]" if is_burst else "DROP [RPM LIMIT]")
        }

if __name__ == "__main__":
    model = PipelinePhysics()
    print("=" * 70)
    print("  VoltGuard: Fluid Dynamics & Pipe Burst Physics Baseline (SciPy)  ")
    print("=" * 70)

    scenarios = [
        ("Normal Safe Setpoint", 1800, 1800),
        ("Safe Transition Step", 1800, 2400),
        ("Sub-Operational Cavitation", 1800, 300),
        ("Malicious Exploit (50,000 RPM)", 1800, 50000)
    ]

    for name, curr, tgt in scenarios:
        res = model.evaluate_setpoint(curr, tgt)
        print(f"\n[SCENARIO] {name} -> Setpoint: {tgt} RPM")
        print(f"  Discharge Velocity : {res['velocity_m_s']} m/s")
        print(f"  Peak Total Pressure: {res['peak_pressure_bar']} Bar (Max Limit: 16.0 Bar)")
        print(f"  Physics Verdict    : {res['verdict']}")