#pragma once
#include <cstdint>
#include <cstddef>

#pragma pack(push, 1)

// Standard 12-Byte Modbus/TCP MBAP + PDU Frame Header
struct ModbusTcpHeader {
    uint16_t transaction_id;   // Bytes 0-1: Transaction Identifier
    uint16_t protocol_id;      // Bytes 2-3: 0x0000 for Modbus
    uint16_t length;           // Bytes 4-5: Number of following bytes
    uint8_t  unit_id;          // Byte 6: Unit / Slave address
    uint8_t  function_code;    // Byte 7: Modbus Function Code (e.g. 0x10)
    uint16_t starting_address; // Bytes 8-9: Target Register Address (Big-Endian)
    uint16_t register_value;   // Bytes 10-11: Value to write (Commanded RPM)
};

#pragma pack(pop)

static_assert(sizeof(ModbusTcpHeader) == 12, "ModbusTcpHeader must be exactly 12 bytes aligned");
