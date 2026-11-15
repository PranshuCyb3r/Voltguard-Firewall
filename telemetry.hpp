#pragma once
#include <cstdint>
#include <cstddef>

#pragma pack(push, 1)

// Exactly 32-Byte Memory Aligned Binary Telemetry Frame for UDP 5555 Stream
struct TelemetryFrame {
    uint32_t timestamp_us;      // 4 Bytes: Microsecond wire timestamp
    uint16_t transaction_id;    // 2 Bytes: Modbus Tx ID
    uint16_t commanded_rpm;     // 2 Bytes: Commanded shaft velocity
    float    pressure_shock;    // 4 Bytes: Joukowsky fluid surge pressure (Bar)
    uint16_t twin_rpm;          // 2 Bytes: RK4 Digital Twin dynamic state
    float    fatigue_score;     // 4 Bytes: Cumulative mechanical fatigue (0-100)
    uint8_t  verdict;           // 1 Byte : 0=ALLOW, 1=DROP_MAX_RPM, 2=DROP_SHOCK, 3=DROP_FATIGUE, 4=DROP_CAVITATION
    uint8_t  reserved[13];      // 13 Bytes: Strict alignment padding to reach 32 bytes
};

#pragma pack(pop)

static_assert(sizeof(TelemetryFrame) == 32, "TelemetryFrame must be exactly 32 bytes aligned");