#pragma once
#include <cstdint>
#include <cstddef>

#pragma pack(push, 1)

// Standard 12-Byte Modbus/TCP MBAP Frame (FC:06 Write Single Register)
struct ModbusTCPFrame {
    uint16_t transaction_id;   // 2 Bytes: Unique sequence ID
    uint16_t protocol_id;      // 2 Bytes: 0x0000 (Modbus)
    uint16_t length;           // 2 Bytes: Remaining bytes (0x0006)
    uint8_t  unit_id;          // 1 Byte:  Target PLC device address
    uint8_t  function_code;    // 1 Byte:  0x06 (Write Single Register)
    uint16_t register_address; // 2 Bytes: Register address (e.g., 0x0001)
    uint16_t register_value;   // 2 Bytes: Commanded payload (e.g., Target RPM)
};

#pragma pack(pop)

static_assert(sizeof(ModbusTCPFrame) == 12, "ModbusTCPFrame must be exactly 12 bytes aligned");