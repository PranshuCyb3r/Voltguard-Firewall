#ifndef MODBUS_FRAME_HPP
#define MODBUS_FRAME_HPP

#include <cstdint>

// Memory Packing: Compiler ko bolta hai ki beech me koi extra padding byte na jode
#pragma pack(push, 1)
struct ModbusTCPHeader {
    uint16_t transaction_id; // Unique ID (Har request ka alag number)
    uint16_t protocol_id;    // Modbus TCP me ye hamesha 0x0000 hota hai
    uint16_t length;         // Aage aane wale bytes ki ginti (Usually 6)
    uint8_t  unit_id;        // Machine ka address (jaise Pump 1 ya Valve 2)
    uint8_t  function_code;  // Kaam kya karna hai? 0x06 = Register me nayi value likho
    uint16_t register_addr;  // Kaunsa register? (300 = Pump Speed Register)
    uint16_t register_val;   // Kitni value set karni hai? (jaise 3,200 RPM ya 50,000 RPM)
};
#pragma pack(pop)

// Endianness Swap Function:
// Network wire par data "Big-Endian" me chalta hai, lekin hamara Intel/AMD CPU "Little-Endian" hota hai.
// Isliye 2 bytes ko palatna zaroori hota hai taaki sahi number read ho.
inline uint16_t swap_endian16(uint16_t val) {
    return (val << 8) | (val >> 8);
}

#endif // MODBUS_FRAME_HPP