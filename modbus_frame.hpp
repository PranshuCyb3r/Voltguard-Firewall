#pragma once
#include <cstdint>
#include <cstddef>

namespace VoltGuard {

    // Endianness converter for 16-bit Modbus integers
    inline uint16_t byteswap16(uint16_t value) {
        return static_cast<uint16_t>((value << 8) | (value >> 8));
    }

#pragma pack(push, 1)
    // Standard 12-Byte Modbus/TCP Master Request Header (FC06 / Single Register)
    struct ModbusTCPHeader {
        uint16_t transaction_id;   // Bytes 0-1
        uint16_t protocol_id;      // Bytes 2-3 (0x0000 for Modbus)
        uint16_t length;           // Bytes 4-5
        uint8_t  unit_id;          // Byte 6
        uint8_t  function_code;    // Byte 7 (e.g. 0x06 Write Single Register)
        uint16_t register_address; // Bytes 8-9 (Target PLC Register)
        uint16_t register_value;   // Bytes 10-11 (Commanded RPM)
    };
#pragma pack(pop)

    static_assert(sizeof(ModbusTCPHeader) == 12, "ModbusTCPHeader must be exactly 12 bytes");
}