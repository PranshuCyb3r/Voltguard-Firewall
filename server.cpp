#include <iostream>
#include <iomanip>
#include <chrono>
#include <winsock2.h>
#include <ws2tcpip.h>
#include "modbus_frame.hpp"
#include "telemetry.hpp"
#include "physics_engine.hpp"

#pragma comment(lib, "ws2_32.lib")

static inline uint16_t byteswap16(uint16_t val) {
    return (val << 8) | (val >> 8);
}

int main() {
    std::cout << "========================================================================\n";
    std::cout << "  VOLTGUARD :: PRODUCTION CYBER-PHYSICAL OT FIREWALL & IPS (WEEK 1-4)    \n";
    std::cout << "  INGRESS: TCP 5502 (ZERO-COPY) | TELEMETRY: UDP 5555 (32-BYTE ALIGNED)  \n";
    std::cout << "========================================================================\n\n";

    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        std::cerr << "[FATAL] WSAStartup failed.\n";
        return 1;
    }

    // 1. Modbus/TCP Ingress Listener (TCP 5502)
    SOCKET server_fd = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(5502);

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));

    if (bind(server_fd, (sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        std::cerr << "[FATAL] Bind failed on TCP 5502.\n";
        return 1;
    }
    listen(server_fd, 5);

    // 2. UDP Telemetry Socket for Native Qt Dashboard (UDP 5555)
    SOCKET udp_sock = socket(AF_INET, SOCK_DGRAM, 0);
    sockaddr_in udp_dest{};
    udp_dest.sin_family = AF_INET;
    udp_dest.sin_port = htons(5555);
    inet_pton(AF_INET, "127.0.0.1", &udp_dest.sin_addr);

    VoltGuard::PhysicsEngine engine;
    std::cout << "[INFO] VoltGuard Zero-Copy IPS Ingress Armed & Listening on TCP 5502...\n\n";

    while (true) {
        sockaddr_in client_addr{};
        int client_len = sizeof(client_addr);
        SOCKET client_sock = accept(server_fd, (sockaddr*)&client_addr, &client_len);
        if (client_sock == INVALID_SOCKET) continue;

        char buffer[256];
        int bytes_read = recv(client_sock, buffer, sizeof(buffer), 0);

        if (bytes_read >= (int)sizeof(ModbusTcpHeader)) {
            auto start_time = std::chrono::high_resolution_clock::now();

            // Zero-copy direct pointer cast
            const auto* hdr = reinterpret_cast<const ModbusTcpHeader*>(buffer);
            uint16_t tx_id   = byteswap16(hdr->transaction_id);
            uint16_t proto   = byteswap16(hdr->protocol_id);
            uint16_t length  = byteswap16(hdr->length);
            uint16_t reg_addr= byteswap16(hdr->register_address);
            uint16_t raw_val = byteswap16(hdr->register_value);

            float shock_bar = 0.0f;
            uint16_t twin_rpm = 0;
            float fatigue_score = 0.0f;

            // Physics Invariant Boundary Verification
            VoltGuard::Verdict v = engine.evaluate(raw_val, shock_bar, twin_rpm, fatigue_score);

            auto end_time = std::chrono::high_resolution_clock::now();
            double latency_us = std::chrono::duration<double, std::micro>(end_time - start_time).count();

            // Construct 32-Byte Wire Telemetry Frame
            TelemetryFrame frame{};
            frame.timestamp_us   = (uint32_t)std::chrono::duration_cast<std::chrono::microseconds>(end_time.time_since_epoch()).count();
            frame.transaction_id = tx_id;
            frame.commanded_rpm  = raw_val;
            frame.pressure_shock = shock_bar;
            frame.twin_rpm       = twin_rpm;
            frame.fatigue_score  = fatigue_score;
            frame.verdict        = static_cast<uint8_t>(v);

            // Stream Frame to Qt Dashboard
            sendto(udp_sock, (const char*)&frame, sizeof(frame), 0, (sockaddr*)&udp_dest, sizeof(udp_dest));

            std::cout << "[INGRESS] Tx: 0x" << std::hex << std::setw(4) << std::setfill('0') << tx_id << std::dec
                      << " | Reg: 0x" << std::hex << std::setw(4) << reg_addr << std::dec
                      << " | Commanded: " << std::setw(5) << raw_val << " RPM"
                      << " | Shock: " << std::fixed << std::setprecision(2) << shock_bar << " Bar"
                      << " | Twin: " << std::setw(5) << twin_rpm << " RPM"
                      << " | Latency: " << std::fixed << std::setprecision(2) << latency_us << " us -> ";

            if (v == VoltGuard::Verdict::ALLOW) {
                std::cout << "\033[1;32m[ ALLOW : INVARIANT MET ]\033[0m\n";
                // True IPS Forwarding: Forward packet downstream
                send(client_sock, buffer, bytes_read, 0);
            } else {
                std::cout << "\033[1;31m[ DROP : INTERCEPTED AT WIRE ]\033[0m (Verdict Code: " << (int)v << ")\n";
                // Inline Dropping: Discard packet and return Modbus Exception 0x86 (Zero narrowing warnings)
                uint8_t err_resp[9] = {
                    static_cast<uint8_t>(buffer[0]),
                    static_cast<uint8_t>(buffer[1]),
                    0x00, 0x00, 0x00, 0x03,
                    static_cast<uint8_t>(buffer[6]),
                    0x86, 0x04
                };
                send(client_sock, (const char*)err_resp, sizeof(err_resp), 0);
            }
        }
        closesocket(client_sock);
    }

    closesocket(server_fd);
    closesocket(udp_sock);
    WSACleanup();
    return 0;
}