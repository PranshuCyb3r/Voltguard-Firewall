#pragma once
#include <cstdint>
#include <cstddef>

#pragma pack(push, 1)

// Exactly 32-Byte Aligned Production Telemetry Frame
struct TelemetryFrame {
    uint32_t timestamp_us;     // 4 bytes: Microsecond timestamp
    uint16_t tx_id;            // 2 bytes: Modbus Transaction ID
    uint16_t commanded_rpm;    // 2 bytes: Commanded setpoint
    float    joukowsky_shock;  // 4 bytes: Joukowsky surge pressure in Bar
    uint16_t twin_rpm;         // 2 bytes: Digital Twin estimated RPM
    float    basquin_fatigue;  // 4 bytes: Cumulative cyclic fatigue (0-100)
    uint8_t  verdict;          // 1 byte:  0=ALLOW, 1=MAX_RPM, 2=SURGE, 4=CAVITATION, 5=FATIGUE
    uint8_t  reserved[13];     // 13 bytes: Exact alignment padding to total 32 bytes
};

#pragma pack(pop)

static_assert(sizeof(TelemetryFrame) == 32, "TelemetryFrame must be exactly 32 bytes aligned");