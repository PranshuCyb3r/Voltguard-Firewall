#pragma once
#include <cstdint>
#include <cstddef>
#include <winsock2.h>
#include <ws2tcpip.h>

namespace VoltGuard {

#pragma pack(push, 1)
    // Exactly 32-Byte Aligned Live UDP Telemetry Frame
    struct TelemetryFrame {
        uint32_t magic;               // 0x5647544D ("VGTM") [Offset 0..3]
        uint16_t tx_id;               // Modbus Transaction ID [Offset 4..5]
        uint16_t commanded_rpm;       // Ingress RPM commanded [Offset 6..7]
        float    pressure_shock_bar;  // Calculated Joukowsky dynamic shock [Offset 8..11]
        float    twin_estimated_rpm;  // Physics Digital Twin state [Offset 12..15]
        uint8_t  verdict;             // 1 = ALLOW, 0/2/3/4 = DROP [Offset 16]
        uint8_t  reserved[7];         // Explicit padding for 8-byte alignment [Offset 17..23]
        uint64_t timestamp_us;        // Microsecond hardware timestamp [Offset 24..31]
    };
#pragma pack(pop)

    static_assert(sizeof(TelemetryFrame) == 32, "TelemetryFrame must be exactly 32 bytes aligned");

    class TelemetryPublisher {
    private:
        SOCKET udp_sock_;
        sockaddr_in dest_addr_;
        bool initialized_;

    public:
        TelemetryPublisher(const char* ip = "127.0.0.1", uint16_t port = 5555) 
            : udp_sock_(INVALID_SOCKET), initialized_(false) {
            udp_sock_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
            if (udp_sock_ != INVALID_SOCKET) {
                dest_addr_.sin_family = AF_INET;
                dest_addr_.sin_port = htons(port);
                inet_pton(AF_INET, ip, &dest_addr_.sin_addr);
                initialized_ = true;
            }
        }

        ~TelemetryPublisher() {
            if (udp_sock_ != INVALID_SOCKET) {
                closesocket(udp_sock_);
            }
        }

        void publish(const TelemetryFrame& frame) {
            if (initialized_) {
                sendto(udp_sock_, reinterpret_cast<const char*>(&frame), sizeof(TelemetryFrame), 0,
                       reinterpret_cast<sockaddr*>(&dest_addr_), sizeof(dest_addr_));
            }
        }
    };
}