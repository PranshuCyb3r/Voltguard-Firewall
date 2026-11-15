#pragma once
#include <cstdint>
#include <cstddef>

#pragma pack(push, 1)

// Standard 12-Byte Modbus/TCP MBAP Header + Write Single Holding Register PDU
struct ModbusTcpHeader {
    uint16_t transaction_id;    // 2 Bytes: Unique transaction identifier
    uint16_t protocol_id;       // 2 Bytes: Modbus protocol identifier (0x0000)
    uint16_t length;            // 2 Bytes: Number of following bytes (0x0006)
    uint8_t  unit_id;           // 1 Byte : Slave / Unit address (0x01)
    uint8_t  function_code;     // 1 Byte : Function Code (0x06: Write Single Register)
    uint16_t register_address;  // 2 Bytes: Holding Register Address (0x0001)
    uint16_t register_value;    // 2 Bytes: Commanded Velocity / Target RPM
};

#pragma pack(pop)

static_assert(sizeof(ModbusTcpHeader) == 12, "ModbusTcpHeader must be exactly 12 bytes packed");