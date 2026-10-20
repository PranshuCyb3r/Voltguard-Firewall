#pragma once

#include <cstdint>
#include <cstddef>
#include <winsock2.h>

namespace VoltGuard {

#pragma pack(push, 1)
struct ModbusTCPHeader {
    uint16_t transaction_id;
    uint16_t protocol_id;
    uint16_t length;
    uint8_t  unit_id;
};
#pragma pack(pop)

struct ParsedFrame {
    uint16_t transaction_id;
    uint16_t protocol_id;
    uint16_t length;
    uint8_t  unit_id;
    uint8_t  function_code;
    uint16_t register_address;
    uint16_t register_value;
};

class ModbusParser {
public:
    // Zero-copy parsing: analyzes raw bytes directly without buffer copies
    static bool parse_frame(const uint8_t* raw_bytes, size_t size, ParsedFrame* out_frame) {
        // Minimum Modbus TCP write frame size: 7 bytes (MBAP) + 5 bytes (PDU) = 12 bytes
        if (size < 12 || out_frame == nullptr || raw_bytes == nullptr) {
            return false;
        }

        const auto* header = reinterpret_cast<const ModbusTCPHeader*>(raw_bytes);

        // Convert big-endian network bytes to host architecture
        out_frame->transaction_id = ntohs(header->transaction_id);
        out_frame->protocol_id    = ntohs(header->protocol_id);
        out_frame->length         = ntohs(header->length);
        out_frame->unit_id        = header->unit_id;

        // Protocol ID must always be 0x0000 for standard Modbus TCP
        if (out_frame->protocol_id != 0x0000) {
            return false;
        }

        // Extract PDU (Function Code, Target Register, Payload Value)
        out_frame->function_code = raw_bytes[7];

        uint16_t raw_reg_addr = *reinterpret_cast<const uint16_t*>(&raw_bytes[8]);
        out_frame->register_address = ntohs(raw_reg_addr);

        uint16_t raw_reg_val = *reinterpret_cast<const uint16_t*>(&raw_bytes[10]);
        out_frame->register_value = ntohs(raw_reg_val);

        return true;
    }
};

} // namespace VoltGuard