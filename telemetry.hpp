#pragma once
#include <cstdint>
#include <cstddef>

#pragma pack(push, 1)

// Standard 32-Byte Aligned Real-Time Telemetry Frame for Wire Stream (Port 5555 UDP)
struct TelemetryFrame {
    uint32_t magic;              // 0x56475544 ("VGUD")
    uint16_t transaction_id;     // Modbus Transaction ID
    uint16_t commanded_rpm;      // Ingress requested RPM
    float joukowsky_shock_bar;   // Calculated hydro-mechanical dynamic shock (Bar)
    float digital_twin_rpm;      // RK4 Dynamic Twin Predicted RPM
    float cumulative_fatigue;    // Week 4: Stateful Cumulative Stress Score
    uint8_t verdict;             // 0x00=ALLOW, 0x01..0x06=DROP Reason
    uint8_t reserved[3];         // 4-byte struct alignment padding
    uint64_t timestamp_us;       // Microsecond timestamp
};

#pragma pack(pop)

static_assert(sizeof(TelemetryFrame) == 32, "TelemetryFrame must be exactly 32 bytes aligned");