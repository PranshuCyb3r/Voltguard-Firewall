#pragma once
#include <cstdint>
#include <cstddef>

#pragma pack(push, 1)

// Standard 12-Byte Modbus/TCP MBAP Request Frame (Write Single Register 0x06)
struct ModbusTcpHeader {
    uint16_t transaction_id;   // 2B (Big-Endian)
    uint16_t protocol_id;      // 2B (Must be 0x0000)
    uint16_t length;           // 2B (Number of remaining bytes = 0x0006)
    uint8_t  unit_id;          // 1B (Slave ID)
    uint8_t  function_code;    // 1B (0x06 = Preset/Write Single Register)
    uint16_t register_address; // 2B (0x0001 = Commanded Shaft RPM)
    uint16_t register_value;   // 2B (Commanded Value e.g. 0xC350 for 50,000 RPM)
};

// Strict 32-Byte Aligned Production Telemetry Frame (UDP Broadcast to Qt Dashboard)
struct TelemetryFrame {
    uint64_t timestamp_ns;     // 8 bytes: Unix timestamp in nanoseconds
    uint16_t transaction_id;   // 2 bytes: Modbus TxID
    uint16_t target_register;  // 2 bytes: Register address (0x0001)
    float    injected_rpm;     // 4 bytes: Commanded shaft RPM
    float    joukowsky_bar;    // 4 bytes: Calculated fluid shock pressure
    uint8_t  verdict;          // 1 byte:  1 = ALLOW, 0 = DROP
    uint8_t  reserved[11];     // 11 bytes: Cache alignment padding (Total = exactly 32 bytes)
};

#pragma pack(pop)

static_assert(sizeof(ModbusTcpHeader) == 12, "ModbusTcpHeader must be exactly 12 bytes");
static_assert(sizeof(TelemetryFrame) == 32, "TelemetryFrame must be exactly 32 bytes aligned");