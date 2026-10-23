#pragma once
#include <cstdint>

#pragma pack(push, 1)

// Standard Modbus TCP MBAP Header (7 Bytes) + PDU
struct ModbusTcpHeader {
    uint16_t transaction_id;   // 2 bytes
    uint16_t protocol_id;      // 2 bytes
    uint16_t length;           // 2 bytes
    uint8_t  unit_id;          // 1 byte
    uint8_t  function_code;    // 1 byte
    uint16_t register_address; // 2 bytes
    uint16_t register_value;   // 2 bytes
};

// Exactly 32-Byte Aligned Cache-Line Telemetry Ingestion Struct
// Calculation: 8 (ts) + 2 (tx) + 2 (reg) + 4 (rpm) + 4 (shock) + 1 (verdict) + 11 (pad) = 32 Bytes
struct TelemetryFrame {
    uint64_t timestamp_ns;     // 8 bytes (monotonic clock)
    uint16_t transaction_id;   // 2 bytes
    uint16_t target_register;  // 2 bytes
    float    injected_rpm;     // 4 bytes
    float    joukowsky_bar;    // 4 bytes
    uint8_t  verdict;          // 1 byte (0x01: ALLOW, 0x00: DROP)
    uint8_t  reserved[11];     // 11 bytes strict cache-line padding
};

#pragma pack(pop)

static_assert(sizeof(TelemetryFrame) == 32, "TelemetryFrame must be strictly 32 bytes");
