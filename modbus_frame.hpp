#pragma once
#include <cstdint>
#include <cstring>
#include <winsock2.h> // Windows ntohs ke liye

#pragma pack(push, 1)
namespace VoltGuard {

    // Modbus TCP MBAP Header (7 bytes)
    struct MBAPHeader {
        uint16_t transaction_id;
        uint16_t protocol_id;
        uint16_t length;
        uint8_t  unit_id;
    };

    // Modbus PDU for Write Single Register (Function 0x06)
    struct WriteSingleRegisterPDU {
        uint8_t  function_code;
        uint16_t register_address;
        uint16_t register_value;
    };

    // Full Modbus Packet
    struct ModbusWriteFrame {
        MBAPHeader mbap;
        WriteSingleRegisterPDU pdu;
    };

    struct ParsedFrame {
        uint16_t transaction_id;
        uint16_t protocol_id;
        uint8_t  unit_id;
        uint8_t  function_code;
        uint16_t register_address;
        uint16_t register_value;
    };

    class ModbusParser {
    public:
        static bool parse_frame(const uint8_t* buffer, size_t size, ParsedFrame* out_frame) {
            if (size < sizeof(ModbusWriteFrame) || out_frame == nullptr) {
                return false;
            }

            // Zero-copy direct memory cast
            const auto* frame = reinterpret_cast<const ModbusWriteFrame*>(buffer);

            // Network byte order (Big Endian) to Host (Little Endian)
            out_frame->transaction_id  = ntohs(frame->mbap.transaction_id);
            out_frame->protocol_id     = ntohs(frame->mbap.protocol_id);
            out_frame->unit_id         = frame->mbap.unit_id;
            out_frame->function_code   = frame->pdu.function_code;
            out_frame->register_address = ntohs(frame->pdu.register_address);
            out_frame->register_value   = ntohs(frame->pdu.register_value);

            return true;
        }

        static const char* function_name(uint8_t fc) {
            switch(fc) {
                case 0x01: return "Read Coils";
                case 0x03: return "Read Holding Registers";
                case 0x05: return "Write Single Coil";
                case 0x06: return "Write Single Register";
                case 0x10: return "Write Multiple Registers";
                default:   return "Custom/Unknown OT Function";
            }
        }
    };

} // namespace VoltGuard
#pragma pack(pop)