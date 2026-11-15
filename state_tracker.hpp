#pragma once
#include <cstdint>
#include <cmath>

namespace VoltGuard {

class StateTracker {
private:
    float cumulative_fatigue;
    uint32_t high_stress_cycles;
    float peak_shock_seen;

public:
    StateTracker() 
        : cumulative_fatigue(12.4f),
          high_stress_cycles(0),
          peak_shock_seen(7.75f) {}

    // Multi-parameter S-N Basquin power-law fatigue accumulation
    void record_cycle(float shock_bar, uint16_t rpm) {
        if (shock_bar > peak_shock_seen) {
            peak_shock_seen = shock_bar;
        }

        // Basquin Stress Ratio Exponent (m = 6.2 for industrial pipe steel)
        if (shock_bar > 10.0f) {
            float stress_ratio = shock_bar / 16.0f;
            float fatigue_increment = std::pow(stress_ratio, 6.2f) * 1.8f;
            cumulative_fatigue += fatigue_increment;
            high_stress_cycles++;
        } else {
            // Natural thermal & mechanical relaxation
            if (cumulative_fatigue > 5.0f) {
                cumulative_fatigue -= 0.05f;
            }
        }

        if (cumulative_fatigue > 100.0f) {
            cumulative_fatigue = 100.0f;
        }
    }

    float get_fatigue_score() const {
        return cumulative_fatigue;
    }

    bool is_fatigue_limit_exceeded() const {
        return cumulative_fatigue >= 85.0f;
    }
};

} // namespace VoltGuard