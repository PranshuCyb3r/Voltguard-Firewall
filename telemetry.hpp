#pragma once
#include <cstdint>

#pragma pack(push, 1)

struct TelemetryFrame {
    uint32_t magic_header;       // 0x56475458 ("VGTX" in ASCII) -> 4 Bytes
    uint16_t transaction_id;     // Modbus Transaction ID        -> 2 Bytes
    uint16_t commanded_rpm;      // Wire Ingress RPM             -> 2 Bytes
    float    joukowsky_shock_bar;// Computed Fluid Shock         -> 4 Bytes
    float    twin_predicted_rpm; // RK4 Digital Twin RPM         -> 4 Bytes
    uint8_t  verdict;            // 0=ALLOW, 1=DROP              -> 1 Byte
    uint8_t  reserved[7];        // Exact struct alignment pad   -> 7 Bytes
    uint64_t timestamp_us;       // Microsecond timestamp        -> 8 Bytes
};

#pragma pack(pop)

static_assert(sizeof(TelemetryFrame) == 32, "TelemetryFrame must be exactly 32 bytes aligned");