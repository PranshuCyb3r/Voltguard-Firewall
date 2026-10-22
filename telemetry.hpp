#pragma once
#include <cstdint>

#pragma pack(push, 1)
// 32-Byte Packed Telemetry Struct (Zero-Allocation IPC Stream)
struct TelemetryFrame {
    uint64_t timestamp_ns;   // Ingestion time in nanoseconds
    uint16_t transaction_id; // Modbus Transaction ID
    uint16_t target_register;// Injected register (e.g. 40301)
    float    injected_rpm;   // Commanded RPM value
    float    joukowsky_bar;  // Calculated shockwave pressure (Bar)
    uint8_t  verdict;        // 0x01: ALLOW, 0x00: DROP
    uint8_t  reserved[7];    // 32-byte cache-line padding
};
#pragma pack(pop)