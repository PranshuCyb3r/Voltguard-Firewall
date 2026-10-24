#pragma once
#include <cstdint>
#include <cstddef>

#pragma pack(push, 1)

// 12-Byte Modbus/TCP MBAP Request Frame
struct ModbusTcpHeader {
    uint16_t transaction_id;   // Big-Endian
    uint16_t protocol_id;      // Must be 0x0000
    uint16_t length;           // Number of following bytes (0x0006)
    uint8_t  unit_id;          // Slave ID
    uint8_t  function_code;    // 0x06 (Write Single Register)
    uint16_t register_address; // Register (0x0001)
    uint16_t register_value;   // Value (Big-Endian RPM)
};

// Exact 32-Byte Aligned Production Telemetry Frame
struct TelemetryFrame {
    uint64_t timestamp_ns;     // 8 bytes: Timestamp
    uint16_t transaction_id;   // 2 bytes: Modbus TxID
    uint16_t target_register;  // 2 bytes: Register address
    float    injected_rpm;     // 4 bytes: Commanded shaft RPM
    float    joukowsky_bar;    // 4 bytes: Fluid shock pressure
    uint8_t  verdict;          // 1 byte:  1 = ALLOW, 0 = DROP
    uint8_t  reserved[11];     // 11 bytes: Exact padding (8+2+2+4+4+1+11 = 32)
};

#pragma pack(pop)

static_assert(sizeof(ModbusTcpHeader) == 12, "ModbusTcpHeader must be 12 bytes");
static_assert(sizeof(TelemetryFrame) == 32, "TelemetryFrame must be exactly 32 bytes");